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
            if val.is_real and not val.is_infinite and not val is sp.nan:
                steps.append(r"\text{Substituição direta: } " + self.fmt(val))
                return steps
        except: pass
        
        # Tenta simplificar
        f_simp = sp.cancel(f)
        if f_simp != f:
            steps.append(r"\text{Simplificando: } " + self.fmt(f) + r" \to " + self.fmt(f_simp))
            try:
                val = f_simp.subs(x, ponto)
                if val.is_real:
                     steps.append(r"\text{Resultado: } " + self.fmt(val))
                     return steps
            except: pass
            
        # L'Hopital se for o caso
        numer, denom = f.as_numer_denom()
        steps.append(r"\text{Aplicando L'Hôpital ou análise de graus.}")
        return steps

    # ===== DERIVADAS =====
    def solve_derivative_steps(self, f):
        steps = [r"\textbf{Derivada de } " + self.fmt(f)]
        steps.append(r"\text{Resultado: } " + self.fmt(sp.diff(f, self.x)))
        return steps

    # ===== INTEGRAIS (ATUALIZADO) =====
    def solve_integral_steps(self, f, a=None, b=None):
        x = self.x
        # 1. Integral Indefinida (Antiderivada)
        antiderivada = sp.integrate(f, x)
        steps = [r"\textbf{1. Encontrar a Antiderivada } F(x):"]
        steps.append(r"\int (" + self.fmt(f) + r") dx = " + self.fmt(antiderivada))

        # 2. Se for Integral Definida (com intervalos)
        if a is not None and b is not None:
            steps.append(r"\textbf{2. Teorema Fundamental do Cálculo:}")
            steps.append(r"\int_{" + str(a) + "}^{" + str(b) + "} f(x) dx = F(" + str(b) + ") - F(" + str(a) + ")")
            
            # Calcula F(b) e F(a)
            try:
                Fa = antiderivada.subs(x, a)
                Fb = antiderivada.subs(x, b)
                steps.append(r"F(" + str(b) + ") = " + self.fmt(Fb))
                steps.append(r"F(" + str(a) + ") = " + self.fmt(Fa))
                
                res = Fb - Fa
                steps.append(r"\text{Resultado: } " + self.fmt(Fb) + " - (" + self.fmt(Fa) + ") = " + self.fmt(res))
            except:
                steps.append(r"\text{Cálculo numérico complexo.}")
        else:
            steps.append(r"\text{Resultado Indefinido: } " + self.fmt(antiderivada) + " + C")
            
        return steps


# ===== GERA GRÁFICO =====
def gerar_grafico(f, x_symbol, a=None, b=None):
    try:
        f_np = sp.lambdify(x_symbol, f, "numpy")
        # Define range do gráfico
        start, end = -10, 10
        if a is not None and b is not None and a != "" and b != "":
            try:
                val_a = float(sp.N(a))
                val_b = float(sp.N(b))
                margin = (val_b - val_a) * 0.5
                start, end = val_a - margin, val_b + margin
            except: pass

        x_vals = np.linspace(start, end, 400)
        y_vals = f_np(x_vals)
        
        plt.figure(figsize=(6, 4))
        plt.plot(x_vals, y_vals, color="#0d6efd", label="f(x)")
        
        # Pinta a área se for integral definida
        if a is not None and b is not None:
            try:
                val_a, val_b = float(sp.N(a)), float(sp.N(b))
                x_fill = np.linspace(val_a, val_b, 100)
                y_fill = f_np(x_fill)
                plt.fill_between(x_fill, y_fill, alpha=0.3, color="#0d6efd", label="Área")
            except: pass

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
    # Captura parâmetros extras
    ponto_str = data.get("ponto", "") # Para Limites
    a_str = data.get("a", "")         # Para Integral Definida (Inicio)
    b_str = data.get("b", "")         # Para Integral Definida (Fim)
    
    x = sp.Symbol("x")

    try:
        if not func_str.strip(): return jsonify({"error": "Função vazia."}), 400

        f = sp.sympify(func_str)
        
        # Converte 'a' e 'b' se existirem
        val_a, val_b = None, None
        if operation == "integral" and a_str and b_str:
            val_a = sp.sympify(a_str) # Permite 'pi', 'sqrt(2)', etc
            val_b = sp.sympify(b_str)

        grafico = gerar_grafico(f, x, val_a, val_b)
        steps, result = [], None

        if operation == "derivada":
            steps = solver.solve_derivative_steps(f)
            result = sp.diff(f, x)
        elif operation == "integral":
            # Decide se é definida ou indefinida
            if val_a is not None and val_b is not None:
                steps = solver.solve_integral_steps(f, val_a, val_b)
                result = sp.integrate(f, (x, val_a, val_b))
            else:
                steps = solver.solve_integral_steps(f)
                result = sp.integrate(f, x)
        elif operation == "limite":
            # Tratamento de limite
            pt = sp.oo if ponto_str == "oo" else (-sp.oo if ponto_str == "-oo" else sp.sympify(ponto_str))
            steps = solver.solve_limit_steps(f, pt)
            result = sp.limit(f, x, pt)
        else:
            return jsonify({"error": "Operação inválida."}), 400

        latex_res = sp.latex(result)
        return jsonify({"result": latex_res, "steps": steps, "plot": grafico})

    except Exception as e:
        return jsonify({"error": f"Erro: {str(e)}"}), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)