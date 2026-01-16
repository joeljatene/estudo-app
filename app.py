import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from github import Github
from io import StringIO

# --- Configuração da Página ---
st.set_page_config(page_title="StudyOS GitHub", layout="wide", page_icon="📚")

# --- CONEXÃO COM GITHUB (Lógica de Persistência) ---
class GithubStorage:
    def __init__(self):
        self.token = st.secrets["GITHUB_TOKEN"]
        self.repo_name = st.secrets["REPO_NAME"]
        self.g = Github(self.token)
        self.repo = self.g.get_repo(self.repo_name)

    def load_csv(self, file_path, colunas_padrao):
        """Tenta carregar um CSV do GitHub. Se não existir, retorna um DataFrame vazio."""
        try:
            file_content = self.repo.get_contents(file_path)
            csv_data = file_content.decoded_content.decode("utf-8")
            return pd.read_csv(StringIO(csv_data))
        except:
            return pd.DataFrame(columns=colunas_padrao)

    def save_csv(self, file_path, dataframe, message="Atualizando dados via Streamlit"):
        """Salva o DataFrame como CSV no GitHub (Cria ou Atualiza)"""
        csv_content = dataframe.to_csv(index=False)
        try:
            # Tenta pegar o arquivo para ver se já existe (para atualizar)
            contents = self.repo.get_contents(file_path)
            self.repo.update_file(contents.path, message, csv_content, contents.sha)
            st.toast("Dados salvos no GitHub com sucesso! ☁️", icon="✅")
        except:
            # Se não existe, cria um novo
            self.repo.create_file(file_path, message, csv_content)
            st.toast("Arquivo criado no GitHub! ☁️", icon="✅")

# Inicializa a conexão
try:
    db = GithubStorage()
    conectado = True
except Exception as e:
    st.error(f"Erro ao conectar no GitHub. Verifique os Secrets. Erro: {e}")
    conectado = False

# --- Inicialização de Estado (Carregando do GitHub se possível) ---
if conectado:
    if 'materias' not in st.session_state:
        st.session_state.materias = db.load_csv("materias.csv", ["Materia", "Peso", "Horas_Estudadas"])
    
    if 'historico_revisoes' not in st.session_state:
        st.session_state.historico_revisoes = db.load_csv("revisoes.csv", ["Data", "Materia", "Topico", "Proxima_Revisao"])

if 'cronometro_ativo' not in st.session_state:
    st.session_state.cronometro_ativo = False

# --- FUNÇÕES AUXILIARES ---
def pomodoro_timer(minutos):
    placeholder = st.empty()
    segundos = minutos * 60
    while segundos > 0 and st.session_state.cronometro_ativo:
        mins, secs = divmod(segundos, 60)
        tempo_formatado = '{:02d}:{:02d}'.format(mins, secs)
        placeholder.markdown(f"<h1 style='text-align: center; font-size: 80px;'>{tempo_formatado}</h1>", unsafe_allow_html=True)
        time.sleep(1)
        segundos -= 1
    if st.session_state.cronometro_ativo:
        placeholder.markdown("<h1 style='text-align: center; color: green;'>FIM! 🔔</h1>", unsafe_allow_html=True)
        st.balloons()
        st.session_state.cronometro_ativo = False

# --- INTERFACE ---
st.title("🚀 StudyOS Integrado ao GitHub")

menu = st.sidebar.radio("Navegar", ["Ciclo de Estudos", "Pomodoro", "Revisões"])

# BOTÃO GLOBAL DE SALVAR
st.sidebar.markdown("---")
if st.sidebar.button("💾 SALVAR DADOS NO GITHUB"):
    with st.spinner('Enviando dados para o repositório...'):
        db.save_csv("materias.csv", st.session_state.materias)
        db.save_csv("revisoes.csv", st.session_state.historico_revisoes)

# --- MÓDULO 1: CICLOS ---
if menu == "Ciclo de Estudos":
    st.header("Gerenciador de Matérias")
    col1, col2 = st.columns([1, 2])
    with col1:
        nova_materia = st.text_input("Nome da Matéria")
        peso = st.slider("Peso", 1, 5, 3)
        if st.button("Adicionar"):
            if nova_materia:
                novo_df = pd.DataFrame([{"Materia": nova_materia, "Peso": peso, "Horas_Estudadas": 0}])
                st.session_state.materias = pd.concat([st.session_state.materias, novo_df], ignore_index=True)
                st.success("Adicionado! Lembre de clicar em Salvar no menu lateral.")
    with col2:
        if not st.session_state.materias.empty:
            st.dataframe(st.session_state.materias, use_container_width=True)
            st.bar_chart(st.session_state.materias.set_index("Materia")["Horas_Estudadas"])

# --- MÓDULO 2: POMODORO ---
if menu == "Pomodoro":
    st.header("⏱️ Cronômetro")
    col1, col2 = st.columns(2)
    with col1:
        tempo = st.number_input("Minutos", 25)
        mat = st.selectbox("Matéria", st.session_state.materias["Materia"].unique() if not st.session_state.materias.empty else ["Geral"])
        
        if st.button("▶️ INICIAR"):
            st.session_state.cronometro_ativo = True
            pomodoro_timer(tempo)
            # Log simples ao fim
            if mat != "Geral":
                idx = st.session_state.materias[st.session_state.materias["Materia"] == mat].index[0]
                st.session_state.materias.at[idx, "Horas_Estudadas"] += (tempo/60)
                st.info("Tempo computado! Salve no GitHub para não perder.")
        
        if st.button("⏹️ PARAR"):
            st.session_state.cronometro_ativo = False
            st.rerun()

# --- MÓDULO 3: REVISÕES ---
if menu == "Revisões":
    st.header("Banco de Revisões")
    
    # Formulário para adicionar manualmente (ou viria do Pomodoro)
    with st.expander("Adicionar Revisão Manual"):
        materia_rev = st.selectbox("Matéria", st.session_state.materias["Materia"].unique() if not st.session_state.materias.empty else ["Geral"])
        topico = st.text_input("Tópico")
        if st.button("Agendar Revisão"):
            hoje = datetime.now()
            prox = hoje + timedelta(days=1)
            nova = {"Data": str(hoje.date()), "Materia": materia_rev, "Topico": topico, "Proxima_Revisao": str(prox.date())}
            st.session_state.historico_revisoes = pd.concat([st.session_state.historico_revisoes, pd.DataFrame([nova])], ignore_index=True)
            st.success("Agendado!")

    if not st.session_state.historico_revisoes.empty:
        st.dataframe(st.session_state.historico_revisoes, use_container_width=True)
