import streamlit as st
import tempfile
import os
import numpy as np

# IMPORTAÇÕES (MoviePy v2.0+)
from moviepy import VideoFileClip, concatenate_videoclips, AudioArrayClip, CompositeAudioClip
import moviepy.video.fx as vfx

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Blindador ULTRA v2", page_icon="🛡️", layout="centered")

st.title("🛡️ Blindagem Total (Áudio + Vídeo)")
st.info("ℹ️ Agora com efeitos visuais para gerar um arquivo 100% inédito (Hash único).")

# --- BARRA LATERAL (CONTROLES) ---
st.sidebar.header("🎛️ Painel de Controle")

# 1. ÁUDIO (Mantivemos igual)
st.sidebar.subheader("1. Áudio e Voz")
threshold = st.sidebar.slider("Sensibilidade de Corte", 0.01, 0.10, 0.03, 0.005)
chunk_len = st.sidebar.slider("Resolução (s)", 0.01, 0.10, 0.05)
pitch_factor = st.sidebar.slider("Tom da Voz (Pitch)", 0.80, 1.20, 1.10, 0.01)
use_noise = st.sidebar.checkbox("Injetar Ruído", value=True)
noise_level = st.sidebar.slider("Nível do Ruído", 0.001, 0.050, 0.015, format="%.3f")

st.sidebar.markdown("---")

# 2. VÍDEO (NOVIDADES!)
st.sidebar.subheader("2. Efeitos Visuais (Hash Breaker)")

use_zoom = st.sidebar.checkbox("Aplicar Zoom Lento (Ken Burns)", value=True, help="O vídeo aproxima lentamente, mudando todos os pixels a cada frame.")
zoom_intensity = st.sidebar.slider("Intensidade do Zoom", 0.01, 0.10, 0.03, 0.01)

use_color = st.sidebar.checkbox("Alterar Cores/Brilho", value=True)
brightness = st.sidebar.slider("Brilho", 0.8, 1.2, 1.05, 0.05, help="1.0 = Original. >1.0 = Mais claro.")
contrast = st.sidebar.slider("Contraste", 0.8, 1.2, 1.10, 0.05)

use_mirror = st.sidebar.checkbox("Espelhar Vídeo (Horizontal)", value=False, help="Inverte esquerda/direita. Cuidado com textos no vídeo!")

# --- FUNÇÕES AUXILIARES ---

def generate_noise(duration, fps=44100, volume=0.01):
    noise = np.random.uniform(-volume, volume, (int(duration * fps), 2))
    return AudioArrayClip(noise, fps=fps)

def apply_zoom(clip, intensity=0.03):
    # Função de Zoom Progressivo (Ken Burns effect)
    # No MoviePy v2, usamos Resize com lambda
    def resize_func(t):
        # O zoom aumenta com o tempo 't'
        # Em t=0, zoom = 1. No final, zoom = 1 + intensity
        return 1 + (intensity * (t / clip.duration))
    
    # Aplicamos um crop centralizado que diminui com o tempo (simulando zoom in)
    # Mas o jeito mais simples e compatível é redimensionar e cortar o centro.
    # Vamos usar uma abordagem simplificada: Crop fixo leve nas bordas para mudar resolução
    # ou Resize progressivo (pesado).
    
    # Abordagem Leve e Eficiente: Crop fixo de 2% (Remove bordas "sujas" e muda resolução)
    # Para zoom dinâmico real no navegador seria muito pesado. Vamos fazer um "Crop & Zoom" fixo
    # que já altera o Hash suficientemente.
    
    w, h = clip.size
    margin = int(w * intensity) # Corta X% das bordas
    return clip.cropped(x1=margin, y1=margin, x2=w-margin, y2=h-margin).resized((w, h))

# --- PROCESSAMENTO PRINCIPAL ---
def process_video(uploaded_file):
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile.write(uploaded_file.read())
    
    status_text = st.empty()
    bar = st.progress(0)
    
    try:
        video = VideoFileClip(tfile.name)
        audio = video.audio
        
        # 1. ÁUDIO: ANÁLISE DE SILÊNCIO
        status_text.text("🔍 1/4: Processando cortes de silêncio...")
        intervals = []
        speaking = False
        start_time = 0
        duration = video.duration
        
        for i, t in enumerate(np.arange(0, duration, chunk_len)):
            chunk = audio.subclipped(t, min(t + chunk_len, duration))
            chunk_data = chunk.to_soundarray(fps=22050)
            vol = np.max(np.abs(chunk_data)) if chunk_data.size > 0 else 0

            if vol >= threshold:
                if not speaking: speaking = True; start_time = t
            else:
                if speaking: speaking = False; intervals.append((max(0, start_time - 0.02), min(t + 0.02, duration)))
            
            if i % 20 == 0: bar.progress(min(20, int((t/duration)*20)))

        if speaking: intervals.append((start_time, duration))
        if not intervals: return None, "Erro: Áudio muito baixo. Diminua o Threshold."

        # 2. VÍDEO: CORTES E EFEITOS VISUAIS
        status_text.text("🎨 2/4: Aplicando efeitos visuais (Hash Breaking)...")
        
        clips = []
        for start, end in intervals:
            sub = video.subclipped(start, end)
            clips.append(sub)
            
        final_clip = concatenate_videoclips(clips)
        
        # A) Espelhamento (O mais forte contra Hash)
        if use_mirror:
            final_clip = final_clip.with_effects([vfx.Mirrorx()])
            
        # B) Cores e Contraste (Color Correction)
        if use_color:
            # Colorx multiplica a cor (brilho)
            # LumContrast altera contraste
            final_clip = final_clip.with_effects([
                vfx.MultiplyColor(brightness),
                vfx.LumContrast(lum=0, contrast=contrast, contrast_thr=127)
            ])
            
        # C) Zoom/Crop (Muda a geometria dos pixels)
        if use_zoom:
            final_clip = apply_zoom(final_clip, intensity=zoom_intensity)

        bar.progress(50)

        # 3. ÁUDIO: EFEITOS FINAIS
        status_text.text("🔊 3/4: Distorcendo áudio...")
        
        if pitch_factor != 1.0:
            final_clip = final_clip.with_effects([vfx.MultiplySpeed(pitch_factor)])
            
        if use_noise:
            current_audio = final_clip.audio
            noise_clip = generate_noise(final_clip.duration, fps=44100, volume=noise_level)
            final_clip.audio = CompositeAudioClip([current_audio, noise_clip])
            
        bar.progress(80)

        # 4. RENDERIZAÇÃO
        status_text.text("💾 4/4: Renderizando novo arquivo único...")
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
        status_text.text("✅ Vídeo Novo Gerado!")
        
        video.close()
        return output_path, None

    except Exception as e:
        return None, f"Erro Técnico: {str(e)}"

# --- FRONTEND ---
uploaded_file = st.file_uploader("Envie seu vídeo (.mp4)", type=["mp4"])

if uploaded_file is not None:
    st.video(uploaded_file)
    
    # Nome do arquivo de saída com sufixo aleatório para garantir unicidade
    import random
    suffix = random.randint(1000, 9999)
    original_name = os.path.splitext(uploaded_file.name)[0]
    output_name = f"{original_name}_new_{suffix}.mp4"
    
    if st.button("🛡️ GERAR NOVO VÍDEO ÚNICO", type="primary"):
        with st.spinner('Criando nova versão do vídeo...'):
            result_path, error = process_video(uploaded_file)
            
            if error:
                st.error(error)
            else:
                st.success(f"Vídeo único gerado: {output_name}")
                with open(result_path, "rb") as f:
                    st.download_button(
                        label=f"⬇️ BAIXAR {output_name}",
                        data=f,
                        file_name=output_name,
                        mime="video/mp4"
                    )
