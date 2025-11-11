from flask import Flask, request, jsonify
from flask_cors import CORS
import sympy as sp

app = Flask(__name__)
CORS(app)

class StepSolver:
    def __init__(self):
        self.x = sp.symbols('x')

    def format_latex(self, expr):
        return sp.latex(expr)

    def solve_derivative_steps(self, f):
        steps = []
        steps.append(r"\text{Função original: } " + self.format_latex(f))
        
        # Chama a função recursiva para gerar os passos
        self._recursive_diff(f, steps)
        
        final_res = sp.diff(f, self.x)
        steps.append(r"\text{Simplificando: } " + self.format_latex(final_res))
        return steps

    def _recursive_diff(self, f, steps):
        """
        Analisa a estrutura da expressão para explicar o passo exato com os números.
        """
        x = self.x

        # 1. Regra da Soma/Subtração
        if f.is_Add:
            steps.append(r"\text{Regra da Soma: Derive cada termo separadamente.}")
            terms = f.args
            derivs = []
            for term in terms:
                # Mostra a intenção de derivar cada termo
                steps.append(r"\frac{d}{dx} \left(" + self.format_latex(term) + r"\right)")
                # Se o termo for complexo, mergulha nele (opcional, simplificado aqui)
                derivs.append(sp.diff(term, x))
            
            # Mostra o resultado parcial da soma
            res_interm = sum(derivs)
            steps.append(r"\text{Juntando as derivadas: } " + self.format_latex(res_interm))

        # 2. Regra da Constante Multiplicativa (Ex: 3*x^2)
        elif f.is_Mul and len(f.args) == 2 and f.args[0].is_Number:
            constante = f.args[0]
            funcao = f.args[1]
            steps.append(r"\text{Separe a constante } " + self.format_latex(constante) + r":")
            steps.append(self.format_latex(constante) + r" \cdot \frac{d}{dx} \left(" + self.format_latex(funcao) + r"\right)")
            
            # Resolve a parte da função recursivamente se não for simples
            if not funcao.is_Symbol:
                self._recursive_diff(funcao, steps)
            
            res = constante * sp.diff(funcao, x)
            steps.append(r"\text{Multiplique: } " + self.format_latex(res))

        # 3. Regra do Produto (u * v)
        elif f.is_Mul:
            u = f.args[0]
            v = sp.Mul(*f.args[1:]) # Agrupa o resto se houver mais de 2
            du = sp.diff(u, x)
            dv = sp.diff(v, x)
            
            steps.append(r"\text{Regra do Produto: } (u \cdot v)' = u'v + uv'")
            steps.append(r"\text{Seja } u = " + self.format_latex(u) + r"\text{ e } v = " + self.format_latex(v))
            steps.append(r"u' = " + self.format_latex(du))
            steps.append(r"v' = " + self.format_latex(dv))
            
            steps.append(r"\text{Aplicando: } (" + self.format_latex(du) + r")(" + self.format_latex(v) + r") + (" + self.format_latex(u) + r")(" + self.format_latex(dv) + r")")

        # 4. Regra da Potência (x^n)
        elif f.is_Pow:
            base, exp = f.as_base_exp()
            # Caso simples: x^n
            if base == x and exp.is_Number:
                steps.append(r"\text{Regra da Potência: } \frac{d}{dx}(x^n) = n \cdot x^{n-1}")
                steps.append(r"\text{Para } n=" + self.format_latex(exp) + r": \quad " + self.format_latex(exp) + r" \cdot x^{" + self.format_latex(exp - 1) + r"}")
            
            # Caso Regra da Cadeia: (u)^n
            elif base != x:
                u = base
                n = exp
                du = sp.diff(u, x)
                steps.append(r"\text{Regra da Cadeia (Potência): } \frac{d}{dx}(u^n) = n \cdot u^{n-1} \cdot u'")
                steps.append(r"\text{Onde } u = " + self.format_latex(u))
                steps.append(r"\text{Derivada externa: } " + self.format_latex(n) + r"(" + self.format_latex(u) + r")^{" + self.format_latex(n-1) + r"}")
                steps.append(r"\text{Derivada interna (u'): } " + self.format_latex(du))
                steps.append(r"\text{Resultado: } " + self.format_latex(n * u**(n-1) * du))

        # 5. Funções Trigonométricas e Outras
        elif isinstance(f, (sp.sin, sp.cos, sp.tan, sp.exp, sp.log)):
            arg = f.args[0]
            if arg == x:
                steps.append(r"\text{Derivada Imediata de Tabela.}")
            else:
                steps.append(r"\text{Regra da Cadeia: Derive a função de fora, mantenha a de dentro, multiplique pela derivada de dentro.}")
                df_outer = sp.diff(f, arg).subs(arg, sp.Symbol('u')) # Truque para mostrar f'(u)
                du = sp.diff(arg, x)
                steps.append(r"\frac{d}{dx} f(g(x)) = f'(g(x)) \cdot g'(x)")
                steps.append(r"\text{Derivada interna de } " + self.format_latex(arg) + r" \text{ é } " + self.format_latex(du))

        # Caso genérico fallback
        else:
            steps.append(r"\text{Aplique as regras de derivação correspondentes para } " + self.format_latex(f))


    def solve_integral_steps(self, f):
        steps = []
        steps.append(r"\text{Integral: } \int (" + self.format_latex(f) + r") dx")
        
        if f.is_Add:
             steps.append(r"\text{Linearidade: Separe a integral em partes.}")
             terms = f.args
             integral_parts = []
             for term in terms:
                 steps.append(r"\int " + self.format_latex(term) + r" dx")
                 integral_parts.append(sp.integrate(term, self.x))
             
             steps.append(r"\text{Resolvendo cada parte individualmente...}")
             # Mostra o resultado somado
             res = sum(integral_parts)
             steps.append(r"\text{Resultado parcial: } " + self.format_latex(res))

        elif f.is_Pow:
            base, exp = f.as_base_exp()
            if base == self.x and exp != -1:
                steps.append(r"\text{Regra da Potência: } \int x^n dx = \frac{x^{n+1}}{n+1}")
                steps.append(r"\text{Aqui } n=" + self.format_latex(exp) + r", \text{ então: } \frac{x^{" + self.format_latex(exp+1) + r"}}{" + self.format_latex(exp+1) + r"}")
            elif base == self.x and exp == -1:
                steps.append(r"\text{Integral de } 1/x \text{ é } \ln(|x|)")

        elif f.is_Mul and f.args[0].is_Number:
            constante = f.args[0]
            resto = f.args[1]
            steps.append(r"\text{Retire a constante } " + self.format_latex(constante) + r" \text{ da integral.}")
            steps.append(self.format_latex(constante) + r" \cdot \int " + self.format_latex(resto) + r" dx")
            
        final_res = sp.integrate(f, self.x)
        steps.append(r"\text{Adicione a constante: } " + self.format_latex(final_res) + " + C")
        return steps

# --- Rotas do Flask ---

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
            passos = [r"\text{1. Substitua x por } " + str(ponto_str),
                      r"\text{2. Verifique se há indeterminação.}",
                      r"\text{3. O limite converge para o resultado abaixo.}"]

        return jsonify({
            'result': resultado,
            'steps': passos
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)