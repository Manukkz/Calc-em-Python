from flask import Flask, request, jsonify
from flask_cors import CORS
import sympy as sp
import matplotlib
matplotlib.use('Agg') # Backend para servidor (sem janela pop-up)
import matplotlib.pyplot as plt
import numpy as np
import io
import base64

app = Flask(__name__)
CORS(app)

class StepSolver:
    def __init__(self):
        self.x = sp.symbols('x')

    def format_latex(self, expr):
        return sp.latex(expr)

    # --- DERIVADAS ---
    def solve_derivative_steps(self, f):
        steps = []
        steps.append(r"\text{Função: } " + self.format_latex(f))
        self._recursive_diff(f, steps)
        final_res = sp.diff(f, self.x)
        steps.append(r"\text{Resultado: } " + self.format_latex(final_res))
        return steps

    def _recursive_diff(self, f, steps):
        # Heurística simples para explicar regras
        if f.is_Add:
            steps.append(r"\text{Regra da Soma: Derive termo a termo.}")
        elif f.is_Mul:
             if len(f.args) == 2 and f.args[0].is_Number:
                steps.append(r"\text{Regra da Constante: Mantenha o } " + self.format_latex(f.args[0]))
             else:
                steps.append(r"\text{Regra do Produto: } u'v + uv'")
        elif f.is_Pow:
            steps.append(r"\text{Regra do Tombo: } nx^{n-1}")
        elif isinstance(f, (sp.sin, sp.cos, sp.tan, sp.exp, sp.log)):
            steps.append(r"\text{Regra da Cadeia / Tabela.}")

    # --- INTEGRAIS ---
    def solve_integral_steps(self, f):
        steps = []
        steps.append(r"\text{Integral: } \int (" + self.format_latex(f) + r") dx")
        res = sp.integrate(f, self.x)
        steps.append(r"\text{Antiderivada: } " + self.format_latex(res) + " + C")
        return steps

    # --- LIMITES (Lógica Inteligente) ---
    def solve_limit_steps(self, f, ponto):
        steps = []
        x = self.x
        
        # CASO 1: Limite tendendo ao Infinito (Regra dos Graus)
        if ponto == sp.oo or ponto == -sp.oo:
            steps.append(r"\text{Análise de Limite no Infinito } (x \to \infty)")
            
            # Tenta separar numerador e denominador
            numer, denom = sp.fraction(f)
            
            if denom != 1:
                # Pega o grau (maior expoente)
                deg_num = sp.degree(numer, x)
                deg_den = sp.degree(denom, x)
                
                steps.append(r"\text{1. Comparação de Graus (maiores expoentes):}")
                steps.append(r"\text{Grau Numerador: } " + str(deg_num))
                steps.append(r"\text{Grau Denominador: } " + str(deg_den))
                
                if deg_num == deg_den:
                    # Pega os coeficientes líderes
                    lead_num = sp.LC(numer, x)
                    lead_den = sp.LC(denom, x)
                    steps.append(r"\text{Graus iguais } \Rightarrow \text{ Divida os coeficientes líderes.}")
                    steps.append(r"\text{Cálculo: } \frac{" + str(lead_num) + "}{" + str(lead_den) + "}")
                    
                    res = lead_num / lead_den
                    steps.append(r"\text{Resultado converge para: } " + self.format_latex(res))
                    return steps
                
                elif deg_num < deg_den:
                    steps.append(r"\text{Grau de baixo é maior } \Rightarrow \text{ Tende a 0.}")
                    return steps
                
                else:
                    steps.append(r"\text{Grau de cima é maior } \Rightarrow \text{ Tende ao infinito.}")
                    return steps
            else:
                 steps.append(r"\text{Função polinomial: comportamento ditado pelo termo de maior grau.}")

        # CASO 2: Limite em ponto finito
        steps.append(r"\text{1. Substituição direta } x \to " + str(ponto))
        try:
            val = f.subs(x, ponto)
            if val.is_real and not val.is_infinite and not val is sp.nan:
                steps.append(r"\text{Substituição funcionou: } " + self.format_latex(val))
                return steps
        except: pass

        steps.append(r"\text{2. Indeterminação. Simplificando a expressão...}")
        f_simp = sp.cancel(f) # Cancela termos comuns
        if f_simp != f:
             steps.append(r"\text{Simplificado: } " + self.format_latex(f_simp))
             try:
                val = f_simp.subs(x, ponto)
                if val.is_real and not val.is_infinite:
                    steps.append(r"\text{Nova substituição: } " + self.format_latex(val))
                    return steps
             except: pass
        
        steps.append(r"\text{3. Aplicação de L'Hôpital ou Limites Laterais.}")
        return steps

# --- GERADOR DE GRÁFICOS ---
def gerar_grafico(f, x_symbol):
    try:
        f_numpy = sp.lambdify(x_symbol, f, modules=['numpy'])
        x_vals = np.linspace(-10, 10, 400)
        try:
            y_vals = f_numpy(x_vals)
            if isinstance(y_vals, (int, float)): y_vals = np.full_like(x_vals, y_vals)
        except: return None

        plt.figure(figsize=(6, 4))
        plt.plot(x_vals, y_vals, label='f(x)', color='#0d6efd')
        plt.axhline(0, color='black', linewidth=0.8)
        plt.axvline(0, color='black', linewidth=0.8)
        plt.grid(color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
        plt.legend()
        plt.title("Visualização")
        
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode()
        plt.close()
        return plot_url
    except: return None

# --- ROTAS ---
solver = StepSolver()

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    func_str = data.get('func_str')
    operation = data.get('operation')
    x = sp.symbols('x')
    
    try:
        f = sp.sympify(func_str)
        passos = []
        grafico = gerar_grafico(f, x)

        if operation == 'derivada':
            passos = solver.solve_derivative_steps(f)
            resultado = sp.latex(sp.diff(f, x))
        elif operation == 'integral':
            passos = solver.solve_integral_steps(f)
            resultado = sp.latex(sp.integrate(f, x))
        elif operation == 'limite':
            ponto_str = data.get('ponto', '0')
            if ponto_str == 'oo': ponto = sp.oo
            elif ponto_str == '-oo': ponto = -sp.oo
            else:
                try: ponto = float(ponto_str)
                except: ponto = 0
            
            resultado = sp.latex(sp.limit(f, x, ponto))
            passos = solver.solve_limit_steps(f, ponto)

        return jsonify({'result': resultado, 'steps': passos, 'plot': grafico})

    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)