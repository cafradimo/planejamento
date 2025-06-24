import streamlit as st
import pandas as pd
import locale
from datetime import datetime, date, timedelta
import calendar
from fpdf import FPDF
import tempfile
import os
from PIL import Image

# Configurar locale para português Brasil com fallback seguro
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
        except locale.Error:
            st.warning("Não foi possível configurar o locale para português. Algumas formatações podem não estar corretas.")

# ======================================
# CONFIGURAÇÃO INICIAL
# ======================================
st.set_page_config(page_title="Sistema de Fiscalização", layout="wide")

# Verificar se o arquivo de logo existe antes de exibir
LOGO_PATH = "10.png"
if os.path.exists(LOGO_PATH):
    try:
        st.image(LOGO_PATH, width=400)
    except Exception as e:
        st.warning(f"Não foi possível carregar a logo: {e}")
        
st.title("Planejamento de Fiscalização")

MESES_PTBR = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
]

DIAS_SEMANA_COMPLETO = {
    0: 'Segunda-feira',
    1: 'Terça-feira',
    2: 'Quarta-feira',
    3: 'Quinta-feira',
    4: 'Sexta-feira',
    5: 'Sábado',
    6: 'Domingo'
}

# ======================================
# 1. FUNÇÃO PARA GERAR PDF COM LOGO
# ======================================
def gerar_relatorio_pdf(agente, municipio, bairro, mes, ano, semana_selecionada, semanas):
    class PDF(FPDF):
        def header(self):
            if os.path.exists(LOGO_PATH):
                try:
                    img = Image.open(LOGO_PATH)
                    self.image(LOGO_PATH, x=10, y=8, w=60)
                    self.set_y(25)
                except Exception as e:
                    print(f"Erro ao carregar logo: {e}")
            
            self.set_font('Arial', 'B', 16)
            self.cell(0, 10, 'Planejamento Semanal', 0, 1, 'C')
            self.ln(5)
            
            self.set_font('Arial', '', 12)
            self.cell(0, 6, f'Agente: {agente}', 0, 1)
            self.cell(0, 6, f'Período: {MESES_PTBR[mes-1]} de {ano}', 0, 1)
            self.cell(0, 6, f'Município: {municipio}', 0, 1)
            self.cell(0, 6, f'Bairro: {bairro}', 0, 1)
            self.ln(10)
        
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')
    
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, f'{semana_selecionada}ª Semana', 0, 1)
    pdf.ln(5)
    pdf.set_font('Arial', '', 12)
    
    semana = semanas[semana_selecionada-1]
    for dia, nome_completo in semana:
        chave = f"{ano}-{mes}-{dia}"
        acoes = st.session_state.planejamento.get(chave, [])
        pdf.cell(0, 8, f'{nome_completo} {dia:02d}/{mes:02d}:', 0, 1)
        
        if acoes:
            for acao in acoes:
                pdf.cell(10)
                pdf.multi_cell(0, 8, f'- {acao}')
        else:
            pdf.cell(10)
            pdf.cell(0, 8, '-', 0, 1)
        pdf.ln(2)
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    temp_path = temp_file.name
    pdf.output(temp_path)
    temp_file.close()
    return temp_path

# ======================================
# 2. CARREGAMENTO DE DADOS
# ======================================
@st.cache_data
def load_agents_data(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file).astype(str)
        required_cols = ['Agente', 'Município', 'Bairro']
        if all(col in df.columns for col in required_cols):
            return df
        else:
            st.error(f"Planilha deve conter: {', '.join(required_cols)}")
            return None
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {e}")
        return None

uploaded_file = st.file_uploader("📂 Carregar planilha de agentes", type=["xlsx", "xls"])

# ======================================
# 3. DATAFRAME DE AÇÕES
# ======================================
def create_actions_df():
    acoes = [
        'AFC','Obras', 'Manutenção Prediais', 'Empresas', 'Postos de Combustíveis', 'Eventos', 
        'Condomínios', 'Estádios', 'Interno', 'Hospitais',
        'Hotéis', 'Agronomia', 'Aeroportos', 'Embarcações', 'Shoppings',
        'Outros'
    ]
    return pd.DataFrame({'Ação': acoes})

df_acoes = create_actions_df()

# ======================================
# 4. FILTROS DE AGENTES
# ======================================
if uploaded_file:
    df_agentes = load_agents_data(uploaded_file)
    
    if df_agentes is not None:
        st.subheader("🔍 Filtros de Agentes")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            municipios = ['Todos'] + sorted(df_agentes['Município'].unique().tolist())
            municipio = st.selectbox("Município", municipios)
            
        with col2:
            bairros = ['Todos'] + sorted(df_agentes['Bairro'].unique().tolist())
            bairro = st.selectbox("Bairro", bairros)
            
        with col3:
            agentes_filtrados = df_agentes.copy()
            if municipio != 'Todos':
                agentes_filtrados = agentes_filtrados[agentes_filtrados['Município'] == municipio]
            if bairro != 'Todos':
                agentes_filtrados = agentes_filtrados[agentes_filtrados['Bairro'] == bairro]
            
            agentes = sorted([str(a) for a in agentes_filtrados['Agente'].unique() if pd.notna(a)])
            agente = st.selectbox("Agente", agentes)

# ======================================
# 5. SELEÇÃO DE PERÍODO
# ======================================
st.subheader("📅 Seleção de Período")

ano_atual = datetime.now().year
mes_atual = datetime.now().month

col1, col2 = st.columns(2)
with col1:
    ano = st.selectbox("Ano", range(ano_atual, ano_atual + 3), index=0)
with col2:
    mes = st.selectbox("Mês", range(1, 13), format_func=lambda x: MESES_PTBR[x-1], index=mes_atual-1)

# ======================================
# 6. PLANEJAMENTO SEMANAL
# ======================================
def get_semanas_mes(year, month):
    semanas = []
    cal = calendar.monthcalendar(year, month)
    
    for semana_cal in cal:
        dias_semana = []
        for i in range(0, 5):  # Pegar apenas dias úteis (segunda a sexta)
            dia = semana_cal[i] if i < len(semana_cal) else 0
            if dia != 0:
                data = date(year, month, dia)
                nome_completo = DIAS_SEMANA_COMPLETO[data.weekday()]
                dias_semana.append((dia, nome_completo))
        
        if dias_semana:
            semanas.append(dias_semana)
    
    # Garantir que temos 5 semanas
    while len(semanas) < 5:
        semanas.append([])
    
    return semanas[:5]

semanas = get_semanas_mes(ano, mes)

if 'planejamento' not in st.session_state:
    st.session_state.planejamento = {}

if 'outras_acoes' not in st.session_state:
    st.session_state.outras_acoes = {}

st.subheader("🗓️ Planejamento Mensal")

for num_semana, semana in enumerate(semanas, 1):
    st.markdown(f"### {num_semana}ª Semana")
    cols = st.columns(5)
    
    for i, (dia, nome_completo) in enumerate(semana):
        with cols[i % 5]:
            st.markdown(f"**{nome_completo} {dia:02d}**" if dia else "** - **")
            
            if dia:
                chave = f"{ano}-{mes}-{dia}"
                if chave not in st.session_state.planejamento:
                    st.session_state.planejamento[chave] = []
                
                if chave not in st.session_state.outras_acoes:
                    st.session_state.outras_acoes[chave] = []
                
                acoes_selecionadas = st.multiselect(
                    f"Selecione as ações para {nome_completo} {dia:02d}",
                    options=df_acoes['Ação'].unique(),
                    default=[a for a in st.session_state.planejamento[chave] if a in df_acoes['Ação'].unique()],
                    key=f"acoes_{chave}"
                )
                
                if 'Outros' in acoes_selecionadas:
                    nova_acao = st.text_input(
                        f"Digite uma nova ação para {nome_completo} {dia:02d}",
                        key=f"nova_acao_{chave}"
                    )
                    
                    if nova_acao and st.button(f"Adicionar ação para {nome_completo} {dia:02d}", key=f"btn_add_{chave}"):
                        if nova_acao not in st.session_state.outras_acoes[chave]:
                            st.session_state.outras_acoes[chave].append(nova_acao)
                            st.session_state.planejamento[chave].append(nova_acao)
                            st.rerun()
                
                if st.session_state.outras_acoes[chave]:
                    st.markdown("**Ações personalizadas:**")
                    for acao in st.session_state.outras_acoes[chave]:
                        st.markdown(f"- {acao}")
                        
                        if st.button(f"Remover '{acao}'", key=f"btn_rm_{chave}_{acao}"):
                            st.session_state.outras_acoes[chave].remove(acao)
                            if acao in st.session_state.planejamento[chave]:
                                st.session_state.planejamento[chave].remove(acao)
                            st.rerun()
                
                acoes_finais = [a for a in acoes_selecionadas if a != 'Outros'] + st.session_state.outras_acoes[chave]
                st.session_state.planejamento[chave] = acoes_finais
                
                if acoes_finais:
                    st.info("Ações selecionadas: " + ", ".join(acoes_finais))

# ======================================
# 7. GERAR RELATÓRIO PDF
# ======================================
if uploaded_file and df_agentes is not None and semanas:
    st.subheader("📄 Gerar Relatório PDF")
    
    semanas_disponiveis = [f"{i}ª Semana" for i in range(1, len(semanas)+1)]
    semana_relatorio = st.selectbox("Selecione a semana para gerar relatório", semanas_disponiveis)
    num_semana = int(semana_relatorio[0])
    
    if st.button("🖨️ Gerar Relatório PDF"):
        tem_dados = any(
            st.session_state.planejamento.get(f"{ano}-{mes}-{dia}", [])
            for dia, _ in semanas[num_semana-1]
            if dia
        )
        
        if not tem_dados:
            st.warning(f"Nenhuma ação planejada para a {semana_relatorio}")
        else:
            with st.spinner("Gerando relatório..."):
                municipio_formatado = municipio if municipio != 'Todos' else 'Todos os municípios'
                bairro_formatado = bairro if bairro != 'Todos' else 'Todos os bairros'
                
                try:
                    pdf_path = gerar_relatorio_pdf(
                        agente=agente,
                        municipio=municipio_formatado,
                        bairro=bairro_formatado,
                        mes=mes,
                        ano=ano,
                        semana_selecionada=num_semana,
                        semanas=semanas
                    )
                    
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Baixar Relatório PDF",
                            data=f.read(),
                            file_name=f"Relatorio_{agente}_{num_semana}ªSemana_{mes}_{ano}.pdf",
                            mime="application/pdf"
                        )
                    
                    st.success("Relatório gerado com sucesso!")
                    os.unlink(pdf_path)
                except Exception as e:
                    st.error(f"Erro ao gerar relatório: {e}")