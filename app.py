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
        """Formata expressão para LaTeX limpo"""
        return sp.latex(expr)

    # ===== LIMITES (Com L'Hôpital) =====
    def solve_limit_steps(self, f, ponto):
        x = self.x
        steps = []
        
        # Passo 1: Montar o limite
        pt_str = sp.latex(ponto)
        steps.append(r"\textbf{1. Analisar o limite:} \quad \lim_{x \to " + pt_str + "} " + self.fmt(f))

        # Passo 2: Substituição Direta
        try:
            val = f.subs(x, ponto)
            # Se for um número real válido e determinado
            if val.is_real and not val.is_infinite and val is not sp.nan:
                steps.append(r"\text{Substituição direta bem sucedida:}")
                steps.append(r"f(" + pt_str + ") = " + self.fmt(val))
                return steps
        except: pass

        # Passo 3: Checar Indeterminação e L'Hôpital
        numer, denom = f.as_numer_denom()
        
        if denom != 1:
            # Calcula limites separados
            lim_num = sp.limit(numer, x, ponto)
            lim_den = sp.limit(denom, x, ponto)
            
            is_0_0 = (lim_num == 0 and lim_den == 0)
            is_inf = (lim_num.is_infinite and lim_den.is_infinite)
            
            if is_0_0 or is_inf:
                tipo = "0/0" if is_0_0 else r"\infty/\infty"
                steps.append(r"\text{Indeterminação identificada } [" + tipo + r"]. \textbf{Aplicando L'Hôpital:}")
                steps.append(r"\lim_{x \to " + pt_str + r"} \frac{f'(x)}{g'(x)}")
                
                # Derivar Cima e Baixo
                d_num = sp.diff(numer, x)
                d_den = sp.diff(denom, x)
                
                steps.append(r"\text{Derivada do Numerador: } (" + self.fmt(numer) + ")' = " + self.fmt(d_num))
                steps.append(r"\text{Derivada do Denominador: } (" + self.fmt(denom) + ")' = " + self.fmt(d_den))
                
                new_f = d_num / d_den
                steps.append(r"\text{Novo Limite: } \lim_{x \to " + pt_str + "} " + self.fmt(new_f))
                
                # Resultado final do L'Hôpital
                res = sp.limit(new_f, x, ponto)
                steps.append(r"\textbf{Resultado Final: } " + self.fmt(res))
                return steps

        # Passo 4: Tentativa Padrão (Simplificação Algébrica)
        res = sp.limit(f, x, ponto)
        if res == sp.nan:
            steps.append(r"\text{O limite não existe ou é complexo.}")
        else:
            steps.append(r"\text{Por simplificação algébrica: } " + self.fmt(res))
        
        return steps

    # ===== DERIVADAS (Regras Explícitas) =====
    def solve_derivative_steps(self, f):
        x = self.x
        steps = [r"\textbf{Derivada de: } " + self.fmt(f)]
        
        # Tenta identificar a estrutura da função
        
        # 1. REGRA DO QUOCIENTE: f = u/v
        numer, denom = f.as_numer_denom()
        if denom != 1 and denom.has(x):
            steps.append(r"\textbf{Regra do Quociente Identificada:}")
            steps.append(r"\left(\frac{u}{v}\right)' = \frac{u'v - uv'}{v^2}")
            
            u, v = numer, denom
            du = sp.diff(u, x)
            dv = sp.diff(v, x)
            
            steps.append(r"u = " + self.fmt(u) + r", \quad v = " + self.fmt(v))
            steps.append(r"u' = " + self.fmt(du) + r", \quad v' = " + self.fmt(dv))
            
            steps.append(r"\text{Montando a fórmula:}")
            steps.append(r"\frac{(" + self.fmt(du) + ")(" + self.fmt(v) + ") - (" + self.fmt(u) + ")(" + self.fmt(dv) + ")}{(" + self.fmt(v) + ")^2}")
        
        # 2. REGRA DO PRODUTO: f = u * v
        elif f.is_Mul:
            steps.append(r"\textbf{Regra do Produto Identificada:}")
            steps.append(r"(u \cdot v)' = u'v + uv'")
            
            # Tenta separar em dois termos (pega o primeiro como u, resto como v)
            args = f.args
            u = args[0]
            v = f / u 
            
            du = sp.diff(u, x)
            dv = sp.diff(v, x)
            
            steps.append(r"u = " + self.fmt(u) + r", \quad v = " + self.fmt(v))
            steps.append(r"u' = " + self.fmt(du) + r", \quad v' = " + self.fmt(dv))
            
            steps.append(r"\text{Aplicando: } (" + self.fmt(du) + ")(" + self.fmt(v) + ") + (" + self.fmt(u) + ")(" + self.fmt(dv) + ")")

        # 3. REGRA DA CADEIA: f = g(h(x)) -> Ex: sin(x^2), (x+1)^10
        elif f.is_Pow or isinstance(f, (sp.sin, sp.cos, sp.tan, sp.exp, sp.log)):
            # Verifica se o argumento interno não é apenas 'x'
            args = f.args
            if args and len(args) > 0 and args[0] != x and args[0].has(x):
                steps.append(r"\textbf{Regra da Cadeia: } \frac{df}{du} \cdot \frac{du}{dx}")
                u = args[0]
                steps.append(r"\text{Seja } u = " + self.fmt(u))
                du = sp.diff(u, x)
                outer_diff = sp.diff(f, u).subs(u, args[0]) # Derivada externa visual
                steps.append(r"\text{Derivada externa } \times \text{Derivada interna (" + self.fmt(du) + ")}")
        
        # 4. REGRA DA SOMA (Linearidade)
        elif f.is_Add:
             steps.append(r"\text{Soma de funções: Derivar termo a termo.}")
             terms = f.args
             d_terms = [self.fmt(sp.diff(t, x)) for t in terms]
             steps.append(r"\frac{d}{dx} [...] = " + " + ".join(d_terms))

        # Resultado final simplificado
        res = sp.diff(f, x)
        steps.append(r"\textbf{Resultado Simplificado: } " + self.fmt(res))
        return steps

    # ===== INTEGRAIS =====
    def solve_integral_steps(self, f, a=None, b=None):
        x = self.x
        steps = []
        
        # 1. Antiderivada
        antiderivada = sp.integrate(f, x)
        steps.append(r"\textbf{1. Encontrar a Antiderivada (Primitiva):}")
        
        if f.is_Pow:
             steps.append(r"\text{Regra da Potência: } \int x^n dx = \frac{x^{n+1}}{n+1}")
        
        steps.append(r"F(x) = \int (" + self.fmt(f) + r") dx = " + self.fmt(antiderivada))

        # 2. Integral Definida
        if a is not None and b is not None:
            steps.append(r"\textbf{2. Aplicar Teorema Fundamental do Cálculo:}")
            steps.append(r"\int_{a}^{b} f(x) dx = F(b) - F(a)")
            
            try:
                Fa = antiderivada.subs(x, a)
                Fb = antiderivada.subs(x, b)
                
                steps.append(r"F(" + self.fmt(b) + ") = " + self.fmt(Fb))
                steps.append(r"F(" + self.fmt(a) + ") = " + self.fmt(Fa))
                
                res = Fb - Fa
                steps.append(r"\text{Cálculo: } (" + self.fmt(Fb) + ") - (" + self.fmt(Fa) + ")")
                steps.append(r"\textbf{Resultado Final: } " + self.fmt(res))
            except:
                steps.append(r"\text{Erro ao substituir limites. Resultado numérico aproximado:}")
                res = sp.integrate(f, (x, a, b)).evalf()
                steps.append(self.fmt(res))
        else:
            steps.append(r"\textbf{Resultado Final: } " + self.fmt(antiderivada) + " + C")
            
        return steps


# ===== GERA GRÁFICO =====
def gerar_grafico(f, x_symbol, a=None, b=None):
    try:
        f_np = sp.lambdify(x_symbol, f, "numpy")
        
        # Define range inteligente
        start, end = -10, 10
        if a is not None and b is not None:
            try:
                val_a = float(sp.N(a))
                val_b = float(sp.N(b))
                # Margem de 50% extra para cada lado
                margin = max(abs(val_b - val_a) * 0.5, 2) 
                start, end = val_a - margin, val_b + margin
            except: pass

        # Evitar pontos de descontinuidade graves gerando mais pontos
        x_vals = np.linspace(start, end, 600)
        
        try:
            y_vals = f_np(x_vals)
            # Limpar valores muito altos (assíntotas) para o gráfico não ficar feio
            y_vals[y_vals > 50] = np.nan
            y_vals[y_vals < -50] = np.nan
        except:
            return None
        
        plt.figure(figsize=(6, 4))
        plt.plot(x_vals, y_vals, color="#0d6efd", label="f(x)", linewidth=2)
        
        # Pinta a área se for integral definida
        if a is not None and b is not None:
            try:
                val_a, val_b = float(sp.N(a)), float(sp.N(b))
                x_fill = np.linspace(val_a, val_b, 200)
                y_fill = f_np(x_fill)
                # Clip fill também
                y_fill[y_fill > 50] = np.nan
                y_fill[y_fill < -50] = np.nan
                
                plt.fill_between(x_fill, y_fill, alpha=0.3, color="#0d6efd", label="Área")
            except: pass

        plt.axhline(0, color="black", lw=1)
        plt.axvline(0, color="black", lw=1)
        plt.grid(alpha=0.3, linestyle='--')
        plt.legend()
        plt.title(f"${sp.latex(f)}$")
        
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", dpi=100)
        buf.seek(0)
        plt.close()
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        print(f"Erro no plot: {e}")
        return None


solver = StepSolver()


@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.json
    func_str = data.get("func_str", "")
    operation = data.get("operation", "")
    ponto_str = data.get("ponto", "")
    a_str = data.get("a", "")
    b_str = data.get("b", "")
    
    x = sp.Symbol("x")

    try:
        if not func_str.strip(): return jsonify({"error": "Função vazia."}), 400

        # Parse seguro da função
        # Transformations ajudam a entender "2x" como "2*x"
        from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
        trans = standard_transformations + (implicit_multiplication_application,)
        
        f = parse_expr(func_str, transformations=trans)
        
        # Converte parâmetros
        val_a, val_b, pt = None, None, None
        
        if operation == "integral" and a_str and b_str:
            val_a = sp.sympify(a_str)
            val_b = sp.sympify(b_str)
        
        if operation == "limite" and ponto_str:
             if ponto_str == "oo": pt = sp.oo
             elif ponto_str == "-oo": pt = -sp.oo
             else: pt = sp.sympify(ponto_str)

        # Gera gráfico antes (para não interferir com a lógica simbólica)
        grafico = gerar_grafico(f, x, val_a, val_b)
        steps, result = [], None

        if operation == "derivada":
            steps = solver.solve_derivative_steps(f)
            result = sp.diff(f, x)
            
        elif operation == "integral":
            if val_a is not None and val_b is not None:
                steps = solver.solve_integral_steps(f, val_a, val_b)
                result = sp.integrate(f, (x, val_a, val_b))
            else:
                steps = solver.solve_integral_steps(f)
                result = sp.integrate(f, x)
                
        elif operation == "limite":
            if pt is None: pt = 0 # Fallback
            steps = solver.solve_limit_steps(f, pt)
            result = sp.limit(f, x, pt)
            
        else:
            return jsonify({"error": "Operação inválida."}), 400

        return jsonify({
            "result": sp.latex(result), 
            "steps": steps, 
            "plot": grafico
        })

    except Exception as e:
        return jsonify({"error": f"Erro matemático: {str(e)}"}), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)