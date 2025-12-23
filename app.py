import streamlit as st
import tempfile
import os
import numpy as np

# IMPORTAÇÕES DA NOVA VERSÃO
from moviepy import VideoFileClip, concatenate_videoclips, AudioArrayClip, CompositeAudioClip
import moviepy.video.fx as vfx
# Removemos a importação problemática de audio.fx

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Blindador PRO 3.0", page_icon="🛡️", layout="centered")

st.title("🛡️ Blindagem de Vídeo (Versão Estável)")
st.success("Status: Sistema online e pronto para processar.")

# --- CONTROLES LATERAIS ---
st.sidebar.header("🎛️ Configurações")
threshold = st.sidebar.slider("Sensibilidade (Threshold)", 0.01, 0.10, 0.03, 0.005)
chunk_len = st.sidebar.slider("Resolução (s)", 0.01, 0.10, 0.05)

st.sidebar.markdown("---")
use_noise = st.sidebar.checkbox("Injetar Ruído (-50dB)", value=True)
use_speed = st.sidebar.checkbox("Aceleração (1.05x)", value=True)
# Removemos o checkbox de EQ para evitar crash

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
        video = VideoFileClip(tfile.name)
        audio = video.audio
        
        # 1. ANÁLISE DE SILÊNCIO
        status_text.text("🔍 1/3: Mapeando silêncios...")
        intervals = []
        speaking = False
        start_time = 0
        
        duration = video.duration
        
        # Loop seguro de análise
        for i, t in enumerate(np.arange(0, duration, chunk_len)):
            chunk = audio.subclipped(t, min(t + chunk_len, duration))
            
            # Análise de volume segura
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
        status_text.text(f"✂️ 2/3: Aplicando {len(intervals)} cortes de blindagem...")
        clips = [video.subclipped(start, end) for start, end in intervals]
        final_clip = concatenate_videoclips(clips)
        bar.progress(60)

        # 3. EFEITOS ANTI-IA (Aceleração + Ruído)
        status_text.text("🎚️ 3/3: Aplicando ruído e aceleração...")
        
        # Aceleração
        if use_speed:
            final_clip = final_clip.with_effects([vfx.MultiplySpeed(1.05)])

        # Ruído de Fundo (Noise Floor)
        if use_noise:
            current_audio = final_clip.audio
            noise_clip = generate_noise(final_clip.duration, fps=44100, volume=0.005)
            # CompositeAudioClip mistura os dois sons
            final_clip.audio = CompositeAudioClip([current_audio, noise_clip])
            
        bar.progress(80)

        # 4. RENDERIZAÇÃO
        status_text.text("💾 Renderizando arquivo final... (Isso leva +- 1 min)")
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
        
        final_clip.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            preset='ultrafast',
            threads=4,
            logger=None
        )
        
        bar.progress(100)
        status_text.text("✅ Sucesso! Seu vídeo está pronto.")
        
        video.close()
        return output_path, None

    except Exception as e:
        return None, f"Erro Técnico: {str(e)}"

# --- FRONTEND ---
uploaded_file = st.file_uploader("Envie seu vídeo (.mp4)", type=["mp4"])

if uploaded_file is not None:
    st.video(uploaded_file)
    
    if st.button("🛡️ INICIAR BLINDAGEM", type="primary"):
        with st.spinner('Processando...'):
            result_path, error = process_video(uploaded_file)
            
            if error:
                st.error(error)
            else:
                st.balloons()
                st.success("Vídeo Blindado Gerado!")
                with open(result_path, "rb") as f:
                    st.download_button(
                        label="⬇️ BAIXAR VÍDEO AGORA",
                        data=f,
                        file_name="video_blindado_final.mp4",
                        mime="video/mp4"
                    )
