
# 🤖 Range Backtester & FVG Quant Engine (Lisboa Pro)

Repositório quantitativo estruturado rigorosamente com base nos padrões metodológicos de análise e modelação estatística intradiária.

## 📊 Estrutura dos 19 Passos do Modelo
1. **Environment:** Importação segura de `pandas`, `numpy`, `os` e `datetime`.
2. **Data Loading:** Leitura vetorial de dados históricos de 1 minuto.
3. **Data Validation:** Verificação rigorosa de colunas e integridade estrutural.
4. **Data Cleaning & Standardization:** Conversão temporal ajustada para o fuso `Europe/Lisbon`.
5. **Strategy Design:** Modelação de Opening Range Breakout (ORB) e Fair Value Gap (FVG).
6. **ATM & Range Calculation:** Definição matemática de `High`, `Low` e `EQ` (50%).
7. **Construct Setup:** Mapeamento de desequilíbrios direcionais.
8. **Exit Logic:** Gestão mecânica de risco com Take Profit fixo e Stop Loss dinâmico.
9. **Daily PnL Calculation:** Computação matemática de resultados por sessão.
10. **Time-Series Alignment:** Isolamento de contratos e janelas operacionais.
11. **Equity Curve:** Rastreamento do capital acumulado.
12. **Drawdown Analysis:** Identificação estatística de zonas de risco de volatilidade.
13. **Return Distribution:** Avaliação da assimetria do payoff.
14. **Performance Summary:** Cálculo de métricas globais e taxa de acerto.
15. **Worst-Day Stress Study:** Análise sob condições extremas de tendência.
16. **Morning Gamma/Volatility Risk:** Avaliação do comportamento nos primeiros minutos.
17. **Structural Behaviour:** Validação de rejeições baseadas no ponto médio (EQ).
18. **Regime-Dependent Filtering:** Mitigação de perdas em ambientes de consolidação.
19. **Asymmetry in Outcomes:** Conclusão baseada em evidência empírica e ceticismo analítico.
