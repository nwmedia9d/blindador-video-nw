import streamlit as st
import tempfile
import os
import numpy as np

# IMPORTAÇÕES (Compatível com MoviePy v2.0+)
from moviepy import VideoFileClip, concatenate_videoclips, AudioArrayClip, CompositeAudioClip
import moviepy.video.fx as vfx

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Blindador ULTRA", page_icon="🛡️", layout="centered")

st.title("🛡️ Blindagem de Vídeo (Anti-IA)")
st.warning("⚠️ O 'Pitch Shift' altera o tom da voz. Ajuste com cuidado para não ficar ininteligível.")

# --- BARRA LATERAL (CONTROLES) ---
st.sidebar.header("🎛️ Painel de Controle")

st.sidebar.subheader("1. Cortes (Silence Truncation)")
threshold = st.sidebar.slider("Sensibilidade (Threshold)", 0.01, 0.10, 0.03, 0.005, help="Define o volume mínimo para não ser cortado.")
chunk_len = st.sidebar.slider("Resolução (s)", 0.01, 0.10, 0.05)

st.sidebar.markdown("---")
st.sidebar.subheader("2. Distorção de Voz (O Segredo)")

# Pitch Factor: 1.0 é normal. 1.10 é voz fina. 0.90 é voz grossa.
# Alterar a velocidade de reprodução altera o pitch (efeito fita cassete).
pitch_factor = st.sidebar.slider(
    "Tom da Voz (Pitch Shift)", 
    0.80, 1.20, 1.10, 0.01, 
    help="1.10 = Voz mais fina (+10%). IAs odeiam isso."
)

use_noise = st.sidebar.checkbox("Injetar Ruído de Fundo", value=True)
noise_level = st.sidebar.slider("Volume do Ruído", 0.001, 0.050, 0.015, format="%.3f")

# --- FUNÇÃO GERADORA DE RUÍDO ---
def generate_noise(duration, fps=44100, volume=0.01):
    # Gera estática aleatória
    noise = np.random.uniform(-volume, volume, (int(duration * fps), 2))
    return AudioArrayClip(noise, fps=fps)

# --- PROCESSAMENTO PRINCIPAL ---
def process_video(uploaded_file):
    # Salva o arquivo original temporariamente
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile.write(uploaded_file.read())
    
    status_text = st.empty()
    bar = st.progress(0)
    
    try:
        video = VideoFileClip(tfile.name)
        audio = video.audio
        
        # 1. ANÁLISE DE SILÊNCIO
        status_text.text("🔍 1/3: Mapeando silêncios para corte...")
        intervals = []
        speaking = False
        start_time = 0
        duration = video.duration
        
        # Loop otimizado para MoviePy v2
        for i, t in enumerate(np.arange(0, duration, chunk_len)):
            chunk = audio.subclipped(t, min(t + chunk_len, duration))
            
            # Análise segura de volume
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
            return None, "Erro: Áudio muito baixo. Tente diminuir o Threshold."

        # 2. APLICAR CORTES
        status_text.text(f"✂️ 2/3: Removendo {len(intervals)} pausas respiratórias...")
        clips = [video.subclipped(start, end) for start, end in intervals]
        final_clip = concatenate_videoclips(clips)
        bar.progress(60)

        # 3. APLICAR EFEITOS (PITCH + RUÍDO)
        status_text.text("☣️ 3/3: Aplicando Pitch Shift e Ruído...")
        
        # A) Pitch Shift (Via velocidade)
        if pitch_factor != 1.0:
            final_clip = final_clip.with_effects([vfx.MultiplySpeed(pitch_factor)])

        # B) Ruído de Fundo
        if use_noise:
            current_audio = final_clip.audio
            # Gera ruído com a nova duração exata
            noise_clip = generate_noise(final_clip.duration, fps=44100, volume=noise_level)
            final_clip.audio = CompositeAudioClip([current_audio, noise_clip])
            
        bar.progress(80)

        # 4. RENDERIZAÇÃO
        status_text.text("💾 Renderizando arquivo final... Aguarde.")
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
        status_text.text("✅ Vídeo Blindado com Sucesso!")
        
        video.close()
        return output_path, None

    except Exception as e:
        return None, f"Erro Técnico: {str(e)}"

# --- FRONTEND (INTERFACE) ---
uploaded_file = st.file_uploader("Envie seu vídeo (.mp4)", type=["mp4"])

if uploaded_file is not None:
    st.video(uploaded_file)
    
    # Prepara o nome do arquivo de saída
    original_name = uploaded_file.name
    file_name_clean = os.path.splitext(original_name)[0]
    output_name = f"{file_name_clean}_blindado.mp4"
    
    if st.button("🛡️ INICIAR PROCESSO DE BLINDAGEM", type="primary"):
        with st.spinner('O Agente está processando seu vídeo...'):
            result_path, error = process_video(uploaded_file)
            
            if error:
                st.error(error)
            else:
                st.success(f"Pronto! Arquivo gerado: {output_name}")
                
                # Lê o arquivo para permitir o download
                with open(result_path, "rb") as f:
                    st.download_button(
                        label=f"⬇️ BAIXAR {output_name}",
                        data=f,
                        file_name=output_name,
                        mime="video/mp4"
                    )
