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
        self.x = sp.symbols('x')

    def format(self, expr):
        return sp.latex(expr)

    # ==========================================
    # LÓGICA DE DERIVADAS (ATUALIZADA E COMPLETA)
    # ==========================================
    def solve_derivative_steps(self, f):
        steps = []
        steps.append(r"\text{Calculando a derivada de: } " + self.format(f))
        
        # Chama a função recursiva que identifica a regra principal
        self._analyze_derivative(f, steps)
        
        # Resultado final
        final_res = sp.diff(f, self.x)
        steps.append(r"\text{Resultado Final: } f'(x) = " + self.format(final_res))
        return steps

    def _analyze_derivative(self, f, steps):
        x = self.x

        # 1. Regra da Constante
        if f.is_constant(x):
            steps.append(r"\text{Regra da Constante: A derivada de um número é 0.}")
            steps.append(r"\frac{d}{dx}(" + self.format(f) + ") = 0")
            return

        # 2. Regra da Potência Simples (x^n)
        if f.is_Pow and f.base == x and f.exp.is_Number:
            n = f.exp
            steps.append(r"\text{Regra da Potência: } \frac{d}{dx}(x^n) = nx^{n-1}")
            steps.append(r"\text{Tomba o expoente } " + str(n) + r" \text{ e subtrai 1.}")
            steps.append(r"Result: " + self.format(n) + "x^{" + str(n-1) + "}")
            return

        # 3. Regra da Soma e Diferença
        if f.is_Add:
            steps.append(r"\text{Regra da Soma/Diferença: Derive cada termo separadamente.}")
            terms = f.args
            derivs = []
            for term in terms:
                # Mostra a derivada de cada parte
                d_term = sp.diff(term, x)
                steps.append(r"\frac{d}{dx}(" + self.format(term) + ") = " + self.format(d_term))
            return

        # 4. Verificação de Quociente vs Produto vs Múltiplo Constante
        # O SymPy trata divisão como multiplicação por potência negativa.
        # Precisamos separar numerador e denominador manualmente para detectar a Regra do Quociente.
        numer, denom = f.as_numer_denom()

        if denom != 1:
            # É uma Divisão -> Regra do Quociente
            steps.append(r"\text{Regra do Quociente: } \left( \frac{f}{g} \right)' = \frac{f'g - fg'}{g^2}")
            steps.append(r"\text{Onde } f=" + self.format(numer) + r" \text{ e } g=" + self.format(denom))
            
            df = sp.diff(numer, x)
            dg = sp.diff(denom, x)
            
            steps.append(r"f' = " + self.format(df))
            steps.append(r"g' = " + self.format(dg))
            steps.append(r"\text{Aplicando: } \frac{(" + self.format(df) + ")(" + self.format(denom) + ") - (" + self.format(numer) + ")(" + self.format(dg) + ")}{(" + self.format(denom) + ")^2}")
            return

        elif f.is_Mul:
            # Separa constantes e funções
            coeffs = [a for a in f.args if a.is_constant(x)]
            funcs = [a for a in f.args if not a.is_constant(x)]
            
            # 5. Múltiplo Constante
            if coeffs and len(funcs) == 1:
                c = sp.Mul(*coeffs)
                g = funcs[0]
                steps.append(r"\text{Múltiplo Constante: } \frac{d}{dx}[c \cdot f(x)] = c \cdot f'(x)")
                steps.append(r"\text{Mantenha o } " + self.format(c) + r" \text{ e derive } " + self.format(g))
                dg = sp.diff(g, x)
                steps.append(r"\text{Derivada da função: } " + self.format(dg))
                return

            # 6. Regra do Produto
            else:
                steps.append(r"\text{Regra do Produto: } (f \cdot g)' = f'g + fg'")
                u = f.args[0]
                v = sp.Mul(*f.args[1:]) # Agrupa o resto
                du = sp.diff(u, x)
                dv = sp.diff(v, x)
                
                steps.append(r"\text{Sendo } f=" + self.format(u) + r", g=" + self.format(v))
                steps.append(r"\text{Aplicando: } (" + self.format(du) + r")(" + self.format(v) + r") + (" + self.format(u) + r")(" + self.format(dv) + r")")
                return

        # 7. Regra da Cadeia (Funções Compostas)
        # Detecta se é uma função conhecida (sin, cos, exp) mas com argumento complexo
        if hasattr(f, 'args') and len(f.args) == 1:
            arg = f.args[0]
            if arg != x and not arg.is_Number:
                steps.append(r"\text{Regra da Cadeia: } \frac{d}{dx}f(g(x)) = f'(g(x)) \cdot g'(x)")
                steps.append(r"\text{Função externa: } " + str(f.func))
                steps.append(r"\text{Função interna (u): } " + self.format(arg))
                
                du = sp.diff(arg, x)
                df_outer = sp.diff(f, arg).subs(arg, sp.Symbol('u')) # Truque visual
                
                steps.append(r"\text{Derive a externa: } " + self.format(df_outer))
                steps.append(r"\text{Derive a interna (u'): } " + self.format(du))
                steps.append(r"\text{Multiplique: } f'(u) \cdot u'")
                return

        # 8. Funções Específicas
        if isinstance(f, sp.exp):
            steps.append(r"\text{Exponencial: } (e^x)' = e^x")
        elif isinstance(f, sp.log):
            steps.append(r"\text{Logaritmo: } (\ln x)' = \frac{1}{x}")
        elif isinstance(f, sp.sin):
            steps.append(r"\text{Trigonométrica: } (\sin x)' = \cos x")
        elif isinstance(f, sp.cos):
            steps.append(r"\text{Trigonométrica: } (\cos x)' = -\sin x")
        
    # ==========================================
    # INTEGRAIS E LIMITES (MANTIDOS IGUAIS)
    # ==========================================
    def solve_integral_steps(self, f):
        return [r"\text{Integral: } \int (" + self.format(f) + r") dx", 
                r"\text{Resultado: } " + self.format(sp.integrate(f, self.x)) + "+C"]

    def solve_limit_steps(self, f, ponto):
        steps = []
        x = self.x
        steps.append(r"\text{Limite: } x \to " + sp.latex(ponto))
        
        # Lógica de Infinito
        if ponto == sp.oo or ponto == -sp.oo:
            numer, denom = sp.fraction(f)
            if denom != 1:
                deg_num = sp.degree(numer, x)
                deg_den = sp.degree(denom, x)
                steps.append(r"\text{Comparação de Graus no Infinito:}")
                steps.append(r"\text{Grau Num: }" + str(deg_num) + r", \text{Grau Den: }" + str(deg_den))
                if deg_num == deg_den:
                    steps.append(r"\text{Graus iguais: Divida os coeficientes líderes.}")
                elif deg_num < deg_den:
                    steps.append(r"\text{Grau do denominador maior: Tende a 0.}")
                else:
                    steps.append(r"\text{Grau do numerador maior: Tende ao infinito.}")
            return steps

        # Lógica Padrão
        try:
            val = f.subs(x, ponto)
            if val.is_real and not val.is_infinite and not val is sp.nan:
                steps.append(r"\text{Substituição Direta: } " + self.format(val))
                return steps
        except: pass

        steps.append(r"\text{Indeterminação. Simplificando ou usando L'Hôpital...}")
        f_simp = sp.cancel(f)
        if f_simp != f:
            steps.append(r"\text{Simplificado: } " + self.format(f_simp))
        
        return steps

# --- GERADOR DE GRÁFICO ---
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
        plt.title("Gráfico")
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