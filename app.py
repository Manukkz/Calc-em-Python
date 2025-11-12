from flask import Flask, request, jsonify
from flask_cors import CORS
import sympy as sp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
import os

app = Flask(__name__)
CORS(app)

class StepSolver:
    def __init__(self):
        self.x = sp.Symbol("x")

    def fmt(self, expr):
        return sp.latex(expr)

    # ===== LIMITES =====
    def solve_limit_steps(self, f, ponto):
        x = self.x
        steps = [r"\textbf{Cálculo do limite } \lim_{x \to " + str(ponto) + "} " + self.fmt(f)]
        try:
            val = f.subs(x, ponto)
            steps.append(r"\text{Substituindo diretamente: } f(" + str(ponto) + ") = " + self.fmt(val))
            if val.is_real and not val.is_infinite:
                steps.append(r"\text{Resultado finito encontrado.}")
                return steps
        except Exception:
            pass

        f_simp = sp.simplify(f)
        if f_simp != f:
            steps.append(r"\text{Simplificando: } " + self.fmt(f) + r" \Rightarrow " + self.fmt(f_simp))
            val2 = f_simp.subs(x, ponto)
            if val2.is_real and not val2.is_infinite:
                steps.append(r"\text{Substituindo novamente: } " + self.fmt(val2))
                return steps

        numer, denom = sp.fraction(f)
        if denom != 1:
            steps.append(r"\text{Aplicando L'Hôpital (0/0 ou ∞/∞):}")
            fn, fd = sp.diff(numer, x), sp.diff(denom, x)
            lh = fn / fd
            steps.append(r"\text{Derivando numerador e denominador: } f'=" + self.fmt(fn) + ", g'=" + self.fmt(fd))
            val3 = sp.limit(lh, x, ponto)
            steps.append(r"\lim " + self.fmt(lh) + " = " + self.fmt(val3))
            return steps

        if ponto in [sp.oo, -sp.oo]:
            steps.append(r"\text{Analisando comportamento no infinito.}")
            res = sp.limit(f, x, ponto)
            steps.append(r"\text{Resultado: } " + self.fmt(res))
            return steps

        steps.append(r"\text{Não foi possível determinar simbolicamente.}")
        return steps

    # ===== DERIVADAS =====
    def solve_derivative_steps(self, f):
        x = self.x
        steps = [r"\textbf{Derivada de } f(x)=" + self.fmt(f)]
        if f.is_Add:
            steps.append(r"\text{Soma: derive termo a termo.}")
            for t in f.args:
                steps.append(r"\frac{d}{dx}(" + self.fmt(t) + ")=" + self.fmt(sp.diff(t, x)))
        elif f.is_Mul:
            u, v = f.args[0], sp.Mul(*f.args[1:])
            steps.append(r"\text{Produto: } (uv)'=u'v+uv'")
            steps.append(r"u=" + self.fmt(u) + ", v=" + self.fmt(v))
            du, dv = sp.diff(u, x), sp.diff(v, x)
            steps.append(r"f'(x)=" + self.fmt(du*v + u*dv))
        elif f.is_Pow:
            steps.append(r"\text{Potência: } (x^n)'=n x^{n-1}")
            steps.append(r"f'(x)=" + self.fmt(sp.diff(f, x)))
        else:
            steps.append(r"\text{Derivando diretamente.}")
            steps.append(r"f'(x)=" + self.fmt(sp.diff(f, x)))
        steps.append(r"\text{Resultado final: } " + self.fmt(sp.diff(f, x)))
        return steps

    # ===== INTEGRAIS =====
    def solve_integral_steps(self, f):
        x = self.x
        steps = [r"\textbf{Integral de } f(x)=" + self.fmt(f)]
        if f.is_Add:
            steps.append(r"\text{Integral de soma: soma das integrais.}")
            for t in f.args:
                steps.append(r"\int " + self.fmt(t) + r"dx=" + self.fmt(sp.integrate(t, x)) + "+C")
        elif f.is_Mul and any(a.is_constant(x) for a in f.args):
            const = sp.Mul(*[a for a in f.args if a.is_constant(x)])
            var = sp.Mul(*[a for a in f.args if not a.is_constant(x)])
            steps.append(r"\text{Constante fora: } " + self.fmt(const))
            steps.append(r"\int " + self.fmt(f) + r"dx=" + self.fmt(const) + r"\int " + self.fmt(var) + r"dx")
            steps.append(r"=" + self.fmt(const * sp.integrate(var, x)) + "+C")
        else:
            steps.append(r"\text{Integração direta simbólica.}")
            steps.append(r"\int " + self.fmt(f) + r"dx=" + self.fmt(sp.integrate(f, x)) + "+C")
        steps.append(r"\text{Resultado final: } " + self.fmt(sp.integrate(f, x)) + "+C")
        return steps


# ===== GERA GRÁFICO =====
def gerar_grafico(f, x_symbol):
    try:
        f_np = sp.lambdify(x_symbol, f, "numpy")
        x_vals = np.linspace(-10, 10, 400)
        y_vals = f_np(x_vals)
        plt.figure(figsize=(6, 4))
        plt.plot(x_vals, y_vals, color="#0d6efd", label="f(x)")
        plt.axhline(0, color="black", lw=0.7)
        plt.axvline(0, color="black", lw=0.7)
        plt.grid(alpha=0.4)
        plt.legend()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        plt.close()
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


solver = StepSolver()


@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.json
    func_str = data.get("func_str", "")
    operation = data.get("operation", "")
    ponto_str = data.get("ponto", "0")
    x = sp.Symbol("x")

    try:
        if not func_str.strip():
            return jsonify({"error": "Função vazia."}), 400

        f = sp.sympify(func_str)
        grafico = gerar_grafico(f, x)
        steps, result = [], None

        if operation == "derivada":
            steps = solver.solve_derivative_steps(f)
            result = sp.diff(f, x)
        elif operation == "integral":
            steps = solver.solve_integral_steps(f)
            result = sp.integrate(f, x)
        elif operation == "limite":
            if ponto_str == "oo":
                ponto = sp.oo
            elif ponto_str == "-oo":
                ponto = -sp.oo
            else:
                try:
                    ponto = float(ponto_str)
                except ValueError:
                    ponto = 0
            steps = solver.solve_limit_steps(f, ponto)
            result = sp.limit(f, x, ponto)
        else:
            return jsonify({"error": "Operação inválida."}), 400

        latex_res = sp.latex(result)
        return jsonify({"result": latex_res, "steps": steps, "plot": grafico})

    except Exception as e:
        return jsonify({"error": f"Erro interno: {str(e)}"}), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
