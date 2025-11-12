from flask import Flask, request, jsonify
from flask_cors import CORS
import sympy as sp
import matplotlib
matplotlib.use('Agg') # Impede que o Python tente abrir uma janela no servidor
import matplotlib.pyplot as plt
import numpy as np
import io
import base64

app = Flask(__name__)
CORS(app)

# --- Classe Solver (Mesma de antes, omitindo para economizar espaço, mantenha a sua) ---
# (Vou colocar apenas a função nova de gráfico e a rota atualizada)

def gerar_grafico(f, x_symbol):
    """
    Gera um gráfico da função e retorna como string Base64.
    """
    try:
        # Converte a função simbólica (SymPy) para numérica (NumPy)
        # Isso permite calcular milhares de pontos rapidamente
        f_numpy = sp.lambdify(x_symbol, f, modules=['numpy'])
        
        # Cria pontos para o eixo X (de -10 a 10)
        x_vals = np.linspace(-10, 10, 400)
        
        try:
            y_vals = f_numpy(x_vals)
            # Correção para funções constantes (ex: f(x) = 5)
            if isinstance(y_vals, (int, float)):
                y_vals = np.full_like(x_vals, y_vals)
        except:
            return None # Se der erro matemático no gráfico, ignora

        plt.figure(figsize=(6, 4))
        plt.plot(x_vals, y_vals, label=f'f(x)', color='#0d6efd')
        plt.axhline(0, color='black', linewidth=0.8) # Eixo X
        plt.axvline(0, color='black', linewidth=0.8) # Eixo Y
        plt.grid(color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
        plt.legend()
        plt.title("Visualização da Função")
        
        # Salva a imagem na memória (buffer)
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')
        img.seek(0)
        
        # Converte para Base64
        plot_url = base64.b64encode(img.getvalue()).decode()
        plt.close() # Limpa a memória
        
        return plot_url
    except Exception as e:
        print(f"Erro no gráfico: {e}")
        return None

# --- RECOLOCAR SUA CLASSE StepSolver AQUI ---
# (Copie a classe StepSolver do código anterior e cole aqui)
class StepSolver:
    def __init__(self):
        self.x = sp.symbols('x')
    def format_latex(self, expr):
        return sp.latex(expr)
    # ... (mantenha os métodos solve_derivative_steps, _recursive_diff, etc.) ...
    # Para economizar espaço, assumo que você manteve a classe StepSolver aqui.
    # Se não tiver o código dela, me avise que mando o arquivo completo novamente.
    def solve_derivative_steps(self, f):
        steps = []
        steps.append(r"\text{Função: } " + self.format_latex(f))
        self._recursive_diff(f, steps)
        final_res = sp.diff(f, self.x)
        steps.append(r"\text{Resultado: } " + self.format_latex(final_res))
        return steps
        
    def _recursive_diff(self, f, steps):
        x = self.x
        if f.is_Add:
            steps.append(r"\text{Regra da Soma}")
        elif f.is_Mul:
            steps.append(r"\text{Regra do Produto/Constante}")
        elif f.is_Pow:
            steps.append(r"\text{Regra da Potência}")
        else:
            steps.append(r"\text{Regra da Cadeia ou Tabela}")

    def solve_integral_steps(self, f):
        steps = []
        steps.append(r"\text{Integral de } " + self.format_latex(f))
        steps.append(r"\text{Aplique regras de integração.}")
        res = sp.integrate(f, self.x)
        steps.append(r"\text{Resultado: } " + self.format_latex(res) + "+ C")
        return steps
# --------------------------------------------

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
        resultado = ""
        grafico_base64 = None

        # Gera o gráfico para qualquer operação
        grafico_base64 = gerar_grafico(f, x)

        if operation == 'derivada':
            passos = solver.solve_derivative_steps(f)
            resultado = sp.latex(sp.diff(f, x))
            
        elif operation == 'integral':
            passos = solver.solve_integral_steps(f)
            resultado = sp.latex(sp.integrate(f, x))
            
        elif operation == 'limite':
            ponto_str = data.get('ponto', '0')
            ponto = sp.oo if ponto_str == 'oo' else float(ponto_str)
            resultado = sp.latex(sp.limit(f, x, ponto))
            passos = [r"\text{Análise de limite para } x \to " + str(ponto_str)]

        return jsonify({
            'result': resultado,
            'steps': passos,
            'plot': grafico_base64 # Envia a imagem
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run()