from flask import Flask, request, jsonify
from flask_cors import CORS
import sympy as sp
import matplotlib
matplotlib.use('Agg') # Backend não-interativo (essencial para servidores)
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
        steps.append(r"\text{Função original: } " + self.format_latex(f))
        self._recursive_diff(f, steps)
        final_res = sp.diff(f, self.x)
        steps.append(r"\text{Resultado final: } " + self.format_latex(final_res))
        return steps

    def _recursive_diff(self, f, steps):
        x = self.x
        if f.is_Add:
            steps.append(r"\text{Regra da Soma: Derive cada termo separadamente.}")
            # Detalha a derivada de cada termo
            terms = f.args
            derivs = []
            for term in terms:
                derivs.append(sp.diff(term, x))
            steps.append(r"\text{Derivadas dos termos: } " + ", ".join([self.format_latex(d) for d in derivs]))
            
        elif f.is_Mul:
            # Verifica se é constante * função
            if len(f.args) == 2 and f.args[0].is_Number:
                steps.append(r"\text{Regra da Constante: Mantenha o } " + self.format_latex(f.args[0]) + r" \text{ e derive o resto.}")
            else:
                steps.append(r"\text{Regra do Produto: } u'v + uv'")
                
        elif f.is_Pow:
            base, exp = f.as_base_exp()
            if base == x and exp.is_Number:
                steps.append(r"\text{Regra do Tombo: } \frac{d}{dx}x^n = n \cdot x^{n-1}")
            else:
                steps.append(r"\text{Regra da Cadeia (Potência): } n \cdot u^{n-1} \cdot u'")

        elif isinstance(f, (sp.sin, sp.cos, sp.tan, sp.exp, sp.log)):
            steps.append(r"\text{Regra da Cadeia / Tabela para } " + self.format_latex(f))

    # --- INTEGRAIS ---
    def solve_integral_steps(self, f):
        steps = []
        steps.append(r"\text{Problema: } \int (" + self.format_latex(f) + r") dx")
        
        if f.is_Add:
             steps.append(r"\text{Linearidade: Separe a integral em várias partes.}")
        
        res = sp.integrate(f, self.x)
        steps.append(r"\text{Solução: } " + self.format_latex(res) + " + C")
        return steps

    # --- LIMITES (Lógica Inteligente) ---
    def solve_limit_steps(self, f, ponto):
        steps = []
        x = self.x
        
        # Passo 1: Substituição Direta
        steps.append(r"\text{1. Tentativa de Substituição Direta: } x \to " + str(ponto))
        
        try:
            # Tenta calcular apenas substituindo
            val_subs = f.subs(x, ponto)
            
            # Se deu um número real válido e não infinito
            if val_subs.is_real and not val_subs.is_infinite and not val_subs is sp.nan:
                steps.append(r"\text{Substituição funcionou!}")
                steps.append(r"f(" + str(ponto) + r") = " + self.format_latex(val_subs))
                return steps
            else:
                steps.append(r"\text{Substituição resultou em indeterminação ou infinito.}")
        except:
            steps.append(r"\text{Erro matemático na substituição direta (ex: divisão por zero).}")

        # Passo 2: Simplificação Algébrica
        steps.append(r"\text{2. Tentando simplificar a expressão algébrica...}")
        
        # 'cancel' é ótimo para cortar polinômios (x^2-1)/(x-1) -> x+1
        f_simplificada = sp.cancel(f) 
        
        if f_simplificada != f:
            steps.append(r"\text{Expressão simplificada: } " + self.format_latex(f_simplificada))
            
            # Passo 3: Tenta substituir na nova expressão
            try:
                val_final = f_simplificada.subs(x, ponto)
                if val_final.is_real and not val_final.is_infinite:
                     steps.append(r"\text{3. Substituindo na expressão simplificada:}")
                     steps.append(r"Resultado = " + self.format_latex(val_final))
                     return steps
            except:
                pass
        else:
            steps.append(r"\text{Não foi possível simplificar algebraicamente de forma óbvia.}")

        # Se chegou aqui, o Python usou algoritmos mais complexos (L'Hopital interno)
        limit_res = sp.limit(f, x, ponto)
        steps.append(r"\text{3. Cálculo via Limites Laterais / L'Hôpital:}")
        steps.append(r"\text{Resultado converge para: } " + self.format_latex(limit_res))
        
        return steps

# --- GERADOR DE GRÁFICOS ---
def gerar_grafico(f, x_symbol):
    try:
        # Transforma SymPy em função Python rápida (NumPy)
        f_numpy = sp.lambdify(x_symbol, f, modules=['numpy'])
        x_vals = np.linspace(-10, 10, 400)
        
        try:
            y_vals = f_numpy(x_vals)
            # Correção para funções constantes (ex: f(x)=5)
            if isinstance(y_vals, (int, float)):
                y_vals = np.full_like(x_vals, y_vals)
        except:
            return None

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
    except Exception:
        return None

# --- CONFIGURAÇÃO DO SERVIDOR ---
solver = StepSolver()

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    func_str = data.get('func_str')
    operation = data.get('operation')
    
    x = sp.symbols('x')
    
    try:
        # Tenta entender a função digitada
        f = sp.sympify(func_str)
        
        passos = []
        resultado = ""
        
        # Gera gráfico
        grafico = gerar_grafico(f, x)

        if operation == 'derivada':
            passos = solver.solve_derivative_steps(f)
            resultado = sp.latex(sp.diff(f, x))
            
        elif operation == 'integral':
            passos = solver.solve_integral_steps(f)
            resultado = sp.latex(sp.integrate(f, x))
            
        elif operation == 'limite':
            ponto_str = data.get('ponto', '0')
            # Tratamento de infinito
            if ponto_str == 'oo':
                ponto = sp.oo
            else:
                try:
                    ponto = float(ponto_str)
                    if ponto.is_integer(): ponto = int(ponto)
                except:
                    ponto = 0
            
            resultado = sp.latex(sp.limit(f, x, ponto))
            passos = solver.solve_limit_steps(f, ponto)

        return jsonify({
            'result': resultado,
            'steps': passos,
            'plot': grafico
        })

    except Exception as e:
        return jsonify({'error': f"Erro na expressão: {str(e)}"}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)