from flask import Flask, request, jsonify
from flask_cors import CORS
import sympy as sp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import io
import base64

app = Flask(__name__)
CORS(app)

class StepSolver:
    def __init__(self):
        self.x = sp.Symbol('x')

    def format(self, expr):
        return sp.latex(expr)

    # ===============================
    # LIMITES - EXPLICAÇÃO DETALHADA
    # ===============================
    def solve_limit_steps(self, f, ponto):
        x = self.x
        steps = [r"\textbf{Cálculo de Limite: } \lim_{x \to " + str(ponto) + "} " + self.format(f)]

        # 1. Substituição direta
        try:
            val = f.subs(x, ponto)
            steps.append(r"\text{1. Substituindo diretamente: } f(" + str(ponto) + ") = " + self.format(val))
            if val.is_real and not val.is_infinite and not val is sp.nan:
                steps.append(r"\text{Valor finito encontrado, então o limite é: } " + self.format(val))
                return steps
            else:
                steps.append(r"\text{Resultado é indeterminado (0/0, ∞/∞, etc.).}")
        except Exception:
            steps.append(r"\text{Não foi possível substituir diretamente.}")

        # 2. Simplificação algébrica
        f_simpl = sp.simplify(f)
        if f_simpl != f:
            steps.append(r"\text{2. Simplificando a expressão: } " + self.format(f) + r" \Rightarrow " + self.format(f_simpl))
            val = f_simpl.subs(x, ponto)
            if val.is_real and not val.is_infinite:
                steps.append(r"\text{Substituindo novamente: } " + self.format(val))
                return steps

        # 3. Aplicando Regra de L'Hôpital (para 0/0 ou ∞/∞)
        numer, denom = sp.fraction(f)
        if denom != 1:
            steps.append(r"\text{3. Aplicando Regra de L'Hôpital: derive numerador e denominador.}")
            fn = sp.diff(numer, x)
            fd = sp.diff(denom, x)
            steps.append(r"\text{Derivadas: } f'=" + self.format(fn) + r", g'=" + self.format(fd))
            lh = fn / fd
            val = sp.limit(lh, x, ponto)
            steps.append(r"\text{Novo limite após L'Hôpital: } \lim " + self.format(lh) + " = " + self.format(val))
            return steps

        # 4. Caso Infinito
        if ponto in [sp.oo, -sp.oo]:
            steps.append(r"\text{Limite no infinito: analise o termo dominante.}")
            deg = sp.degree(f, x)
            if deg is not None:
                steps.append(r"\text{Maior grau: } " + str(deg))
            res = sp.limit(f, x, ponto)
            steps.append(r"\text{Resultado: } " + self.format(res))
            return steps

        steps.append(r"\text{Não foi possível determinar simbolicamente.}")
        return steps

    # ===============================
    # DERIVADAS - EXPLICAÇÃO DETALHADA
    # ===============================
    def solve_derivative_steps(self, f):
        x = self.x
        steps = [r"\textbf{Derivada de } f(x) = " + self.format(f)]

        # Identificação do tipo de função
        if f.is_Add:
            steps.append(r"\text{Função é uma soma: derive termo a termo.}")
            for term in f.args:
                steps.append(r"\frac{d}{dx}(" + self.format(term) + ") = " + self.format(sp.diff(term, x)))
        elif f.is_Mul:
            steps.append(r"\text{Função é um produto: use a Regra do Produto.}")
            u, v = f.args[0], sp.Mul(*f.args[1:])
            steps.append(r"\text{Seja } u=" + self.format(u) + ", v=" + self.format(v))
            du, dv = sp.diff(u, x), sp.diff(v, x)
            steps.append(r"f'(x) = u'v + uv' = " + self.format(du*v + u*dv))
        elif f.is_Pow:
            steps.append(r"\text{Função é potência: } (x^n)' = n x^{n-1}")
            steps.append(r"f'(x) = " + self.format(sp.diff(f, x)))
        else:
            steps.append(r"\text{Usando regra direta de derivação simbólica.}")
            steps.append(r"f'(x) = " + self.format(sp.diff(f, x)))

        steps.append(r"\text{Resultado final: } f'(x) = " + self.format(sp.diff(f, x)))
        return steps

    # ===============================
    # INTEGRAIS - EXPLICAÇÃO DETALHADA
    # ===============================
    def solve_integral_steps(self, f):
        x = self.x
        steps = [r"\textbf{Integral de } f(x) = " + self.format(f)]

        if f.is_Add:
            steps.append(r"\text{Integral de uma soma é a soma das integrais.}")
            for term in f.args:
                steps.append(r"\int " + self.format(term) + r"\,dx = " + self.format(sp.integrate(term, x)) + "+C")
        elif f.is_Mul and any(a.is_constant(x) for a in f.args):
            const = sp.Mul(*[a for a in f.args if a.is_constant(x)])
            varpart = sp.Mul(*[a for a in f.args if not a.is_constant(x)])
            steps.append(r"\text{Constante fora da integral: } " + self.format(const))
            steps.append(r"\int " + self.format(f) + r"\,dx = " + self.format(const) + r"\int " + self.format(varpart) + r"\,dx")
            steps.append(r"= " + self.format(const * sp.integrate(varpart, x)) + "+C")
        else:
            steps.append(r"\text{Aplicando integração simbólica direta.}")
            steps.append(r"\int " + self.format(f) + r"\,dx = " + self.format(sp.integrate(f, x)) + "+C")

        steps.append(r"\text{Resultado final: } " + self.format(sp.integrate(f, x)) + "+C")
        return steps


# --- GERADOR DE GRÁFICO ---
def gerar_grafico(f, x_symbol):
    try:
        f_numpy = sp.lambdify(x_symbol, f, modules=['numpy'])
        x_vals = np.linspace(-10, 10, 400)
        y_vals = f_numpy(x_vals)
        if isinstance(y_vals, (int, float)):
            y_vals = np.full_like(x_vals, y_vals)

        plt.figure(figsize=(6, 4))
        plt.plot(x_vals, y_vals, color="#0d6efd", label="f(x)")
        plt.axhline(0, color="black", lw=0.8)
        plt.axvline(0, color="black", lw=0.8)
        plt.grid(True, alpha=0.4)
        plt.legend()
        plt.title("Gráfico de f(x)")
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')
        img.seek(0)
        plt.close()
        return base64.b64encode(img.getvalue()).decode()
    except Exception:
        return None


# --- ROTAS ---
solver = StepSolver()

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    func_str = data.get('func_str')
    operation = data.get('operation')
    ponto_str = data.get('ponto', '0')
    x = sp.Symbol('x')

    try:
        f = sp.sympify(func_str)
        grafico = gerar_grafico(f, x)

        if operation == 'derivada':
            steps = solver.solve_derivative_steps(f)
            result = sp.diff(f, x)
        elif operation == 'integral':
            steps = solver.solve_integral_steps(f)
            result = sp.integrate(f, x)
        elif operation == 'limite':
            if ponto_str == 'oo': ponto = sp.oo
