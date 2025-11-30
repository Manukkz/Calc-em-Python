from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sympy as sp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
import os

app = Flask(__name__, template_folder='.')
CORS(app)

class StepSolver:
    def __init__(self):
        self.x = sp.Symbol("x")

    def fmt(self, expr):
        """Formata expressão para LaTeX limpo"""
        return sp.latex(expr)

    # ===== LIMITES (Com L'Hôpital) =====
    def solve_limit_steps(self, f, ponto):
        x = self.x
        steps = []
        pt_str = sp.latex(ponto)
        steps.append(r"\textbf{1. Analisar o limite:} \quad \lim_{x \to " + pt_str + "} " + self.fmt(f))

        try:
            val = f.subs(x, ponto)
            if val.is_real and not val.is_infinite and val is not sp.nan:
                steps.append(r"\text{Substituição direta: } f(" + pt_str + ") = " + self.fmt(val))
                return steps
        except: pass

        numer, denom = f.as_numer_denom()
        if denom != 1:
            lim_num = sp.limit(numer, x, ponto)
            lim_den = sp.limit(denom, x, ponto)
            
            if (lim_num == 0 and lim_den == 0) or (lim_num.is_infinite and lim_den.is_infinite):
                steps.append(r"\text{Indeterminação identificada. Aplicando L'Hôpital:}")
                d_num = sp.diff(numer, x)
                d_den = sp.diff(denom, x)
                
                steps.append(r"\lim_{x \to " + pt_str + r"} \frac{" + self.fmt(d_num) + "}{" + self.fmt(d_den) + "}")
                
                new_f = d_num / d_den
                res = sp.limit(new_f, x, ponto)
                steps.append(r"\textbf{Resultado: } " + self.fmt(res))
                return steps

        res = sp.limit(f, x, ponto)
        steps.append(r"\text{Resultado por análise algébrica: } " + self.fmt(res))
        return steps

    # ===== DERIVADAS =====
    def solve_derivative_steps(self, f):
        x = self.x
        steps = [r"\textbf{Derivada de: } " + self.fmt(f)]
        
        if f.is_Mul:
            steps.append(r"\text{Regra do Produto: } (uv)' = u'v + uv'")
        elif f.is_Pow and f.args[0] != x:
            steps.append(r"\text{Regra da Cadeia: } \frac{df}{du} \cdot \frac{du}{dx}")
            
        res = sp.diff(f, x)
        steps.append(r"\textbf{Resultado Final: } " + self.fmt(res))
        return steps

    # ===== INTEGRAIS =====
    def solve_integral_steps(self, f, a=None, b=None):
        x = self.x
        steps = []
        antiderivada = sp.integrate(f, x)
        steps.append(r"\textbf{Antiderivada: } F(x) = " + self.fmt(antiderivada))

        if a is not None and b is not None:
            steps.append(r"\textbf{Teorema Fundamental do Cálculo: } F(b) - F(a)")
            try:
                Fa = antiderivada.subs(x, a)
                Fb = antiderivada.subs(x, b)
                res = Fb - Fa
                steps.append(r"(" + self.fmt(Fb) + ") - (" + self.fmt(Fa) + ") = " + self.fmt(res))
            except:
                steps.append(r"\text{Cálculo numérico aproximado.}")
        else:
            steps.append(r"\text{Resultado: } " + self.fmt(antiderivada) + " + C")
        return steps

# ===== FUNÇÕES AUXILIARES =====
def gerar_grafico(f, x_symbol, a=None, b=None):
    try:
        f_np = sp.lambdify(x_symbol, f, "numpy")
        start, end = -10, 10
        if a is not None and b is not None:
            try:
                val_a, val_b = float(sp.N(a)), float(sp.N(b))
                margin = max(abs(val_b - val_a) * 0.5, 2)
                start, end = val_a - margin, val_b + margin
            except: pass

        x_vals = np.linspace(start, end, 400)
        try:
            y_vals = f_np(x_vals)
            y_vals[y_vals > 50] = np.nan
            y_vals[y_vals < -50] = np.nan
        except: return None
        
        plt.figure(figsize=(6, 4))
        plt.plot(x_vals, y_vals, color="#0d6efd")
        plt.grid(alpha=0.3)
        plt.axhline(0, color='black', linewidth=0.8)
        plt.axvline(0, color='black', linewidth=0.8)
        
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        plt.close()
        return base64.b64encode(buf.getvalue()).decode()
    except: return None

solver = StepSolver()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.json
    func_str = data.get("func_str", "")
    op = data.get("operation", "")
    pt_str = data.get("ponto", "")
    a_str = data.get("a", "")
    b_str = data.get("b", "")
    
    x = sp.Symbol("x")
    try:
        from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
        trans = standard_transformations + (implicit_multiplication_application,)
        f = parse_expr(func_str, transformations=trans)
        
        val_a, val_b, pt = None, None, None
        if op == "integral" and a_str and b_str:
            val_a, val_b = sp.sympify(a_str), sp.sympify(b_str)
        if op == "limite" and pt_str:
             pt = sp.oo if pt_str == "oo" else (-sp.oo if pt_str == "-oo" else sp.sympify(pt_str))

        grafico = gerar_grafico(f, x, val_a, val_b)
        steps, result = [], None

        if op == "derivada":
            steps = solver.solve_derivative_steps(f)
            result = sp.diff(f, x)
        elif op == "integral":
            if val_a is not None:
                steps = solver.solve_integral_steps(f, val_a, val_b)
                result = sp.integrate(f, (x, val_a, val_b))
            else:
                steps = solver.solve_integral_steps(f)
                result = sp.integrate(f, x)
        elif op == "limite":
            steps = solver.solve_limit_steps(f, pt if pt else 0)
            result = sp.limit(f, x, pt if pt else 0)

        return jsonify({"result": sp.latex(result), "steps": steps, "plot": grafico})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)