import streamlit as st
import tempfile
import os
import numpy as np

# IMPORTAÇÕES DA NOVA VERSÃO (MOVIEPY 2.0+)
# Não usamos mais 'moviepy.editor'
from moviepy import VideoFileClip, concatenate_videoclips, AudioArrayClip, CompositeAudioClip
import moviepy.video.fx as vfx
import moviepy.audio.fx as afx

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Blindador PRO 2.0", page_icon="🛡️", layout="centered")

st.title("🛡️ Blindagem de Vídeo (Versão 2.0)")
st.info("ℹ️ Sistema atualizado para rodar no Python moderno do Streamlit Cloud.")

# --- CONTROLES LATERAIS ---
st.sidebar.header("🎛️ Configurações")
threshold = st.sidebar.slider("Sensibilidade (Threshold)", 0.01, 0.10, 0.03, 0.005)
chunk_len = st.sidebar.slider("Resolução (s)", 0.01, 0.10, 0.05)

st.sidebar.markdown("---")
use_noise = st.sidebar.checkbox("Injetar Ruído (-50dB)", value=True)
use_eq = st.sidebar.checkbox("Equalização Anti-IA", value=True)
use_speed = st.sidebar.checkbox("Aceleração (1.05x)", value=True)

# --- FUNÇÃO GERADORA DE RUÍDO ---
def generate_noise(duration, fps=44100, volume=0.01):
    # Gera ruído branco aleatório
    noise = np.random.uniform(-volume, volume, (int(duration * fps), 2))
    return AudioArrayClip(noise, fps=fps)

# --- PROCESSAMENTO PRINCIPAL ---
def process_video(uploaded_file):
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile.write(uploaded_file.read())
    
    status_text = st.empty()
    bar = st.progress(0)
    
    try:
        # Carrega o vídeo
        video = VideoFileClip(tfile.name)
        audio = video.audio
        
        # 1. ANÁLISE DE SILÊNCIO
        status_text.text("🔍 1/4: Mapeando silêncios...")
        intervals = []
        speaking = False
        start_time = 0
        
        # Convertendo áudio para array para análise rápida
        # MoviePy 2.0 lida com audio arrays de forma diferente, vamos usar iteração segura
        duration = video.duration
        
        for i, t in enumerate(np.arange(0, duration, chunk_len)):
            # Extrair trecho de áudio
            chunk = audio.subclipped(t, min(t + chunk_len, duration))
            
            # Analisar volume (RMS ou Max)
            # Em v2, max_volume() ainda existe, mas convertendo para array é mais seguro
            chunk_data = chunk.to_soundarray(fps=22050)
            if chunk_data.size > 0:
                vol = np.max(np.abs(chunk_data))
            else:
                vol = 0

            if vol >= threshold:
                if not speaking:
                    speaking = True
                    start_time = t
            else:
                if speaking:
                    speaking = False
                    intervals.append((max(0, start_time - 0.02), min(t + 0.02, duration)))
            
            if i % 10 == 0:
                prog = min(30, int((t/duration)*30))
                bar.progress(prog)

        if speaking:
            intervals.append((start_time, duration))
            
        if not intervals:
            return None, "Erro: Nenhum áudio detectado acima do limite. Tente diminuir o Threshold."

        # 2. CORTE E CONCATENAÇÃO
        status_text.text(f"✂️ 2/4: Removendo pausas ({len(intervals)} cortes)...")
        # Nota: 'subclipped' é o novo 'subclip' seguro em v2
        clips = [video.subclipped(start, end) for start, end in intervals]
        final_clip = concatenate_videoclips(clips)
        bar.progress(50)

        # 3. ACELERAÇÃO (Sintaxe V2)
        if use_speed:
            # Em v2, usamos with_effects e MultiplySpeed
            final_clip = final_clip.with_effects([vfx.MultiplySpeed(1.05)])

        # 4. ENGENHARIA DE ÁUDIO
        status_text.text("🎚️ 3/4: Aplicando blindagem de áudio...")
        current_audio = final_clip.audio
        
        if use_eq:
            # Sintaxe v2 para filtros de áudio
            # HighPass e LowPass
            effects = [
                afx.AudioHighPass(100), # Remove graves
                afx.AudioLowPass(8000)  # Remove super agudos
            ]
            current_audio = current_audio.with_effects(effects)
        
        if use_noise:
            noise_clip = generate_noise(final_clip.duration, fps=44100, volume=0.005)
            current_audio = CompositeAudioClip([current_audio, noise_clip])
            
        final_clip.audio = current_audio
        bar.progress(70)

        # 5. RENDERIZAÇÃO
        status_text.text("💾 4/4: Renderizando (Aguarde)...")
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
        
        # preset='ultrafast' ajuda a não dar timeout no servidor gratuito
        final_clip.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            preset='ultrafast',
            threads=4,
            logger=None
        )
        
        bar.progress(100)
        status_text.text("✅ Vídeo Blindado e Pronto!")
        
        video.close()
        return output_path, None

    except Exception as e:
        return None, f"Erro Técnico: {str(e)}"

# --- FRONTEND ---
uploaded_file = st.file_uploader("Envie seu vídeo (.mp4)", type=["mp4"])

if uploaded_file is not None:
    st.video(uploaded_file)
    
    if st.button("🛡️ INICIAR BLINDAGEM", type="primary"):
        with st.spinner('Processando... (Isso pode levar alguns minutos)'):
            result_path, error = process_video(uploaded_file)
            
            if error:
                st.error(error)
            else:
                st.success("Sucesso!")
                with open(result_path, "rb") as f:
                    st.download_button(
                        label="⬇️ BAIXAR VÍDEO BLINDADO",
                        data=f,
                        file_name="video_blindado_v2.mp4",
                        mime="video/mp4"
                    )
