import streamlit as st
import tempfile
import os
import random
import numpy as np

# IMPORTAÇÕES (MoviePy v2.0+)
from moviepy import VideoFileClip, concatenate_videoclips, AudioArrayClip, CompositeAudioClip
import moviepy.video.fx as vfx

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Blindador ULTRA v3", page_icon="🛡️", layout="centered")

st.title("🛡️ Blindagem Total (Hash Breaking)")
st.success("Status: Sistema corrigido e online.")

# --- BARRA LATERAL (CONTROLES) ---
st.sidebar.header("🎛️ Painel de Controle")

# 1. ÁUDIO
st.sidebar.subheader("1. Áudio e Voz")
threshold = st.sidebar.slider("Sensibilidade de Corte", 0.01, 0.10, 0.03, 0.005)
chunk_len = st.sidebar.slider("Resolução (s)", 0.01, 0.10, 0.05)
pitch_factor = st.sidebar.slider("Tom da Voz (Pitch)", 0.80, 1.20, 1.10, 0.01)
use_noise = st.sidebar.checkbox("Injetar Ruído", value=True)
noise_level = st.sidebar.slider("Nível do Ruído", 0.001, 0.050, 0.015, format="%.3f")

st.sidebar.markdown("---")

# 2. VÍDEO
st.sidebar.subheader("2. Efeitos Visuais (Hash Breaker)")

use_zoom = st.sidebar.checkbox("Aplicar Zoom Fixo (Corte de Borda)", value=True, help="Remove as bordas para mudar a resolução e o Hash.")
zoom_intensity = st.sidebar.slider("Intensidade do Zoom", 0.01, 0.10, 0.03, 0.01)

use_color = st.sidebar.checkbox("Alterar Cores/Brilho", value=True)
brightness = st.sidebar.slider("Brilho", 0.8, 1.2, 1.05, 0.05)
contrast = st.sidebar.slider("Contraste", 0.8, 1.2, 1.10, 0.05)

use_mirror = st.sidebar.checkbox("Espelhar Vídeo (Horizontal)", value=False, help="Inverte esquerda/direita. Cuidado com textos!")

# --- FUNÇÕES AUXILIARES ---

def generate_noise(duration, fps=44100, volume=0.01):
    noise = np.random.uniform(-volume, volume, (int(duration * fps), 2))
    return AudioArrayClip(noise, fps=fps)

def apply_zoom_crop(clip, intensity=0.03):
    # VERSÃO TURBO: Apenas corta as bordas, sem redimensionar.
    # Isso muda a resolução (ex: 1920x1080 -> 1860x1040), o que é PERFEITO
    # para quebrar o Hash sem gastar CPU redimensionando.
    w = clip.w
    h = clip.h
    margin_w = int(w * intensity)
    margin_h = int(h * intensity)
    
    # Apenas corta. O vídeo final ficará levemente menor (imperceptível),
    # mas renderizará MUITO mais rápido.
    return clip.cropped(x1=margin_w, y1=margin_h, x2=w-margin_w, y2=h-margin_h)

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
        
        # Loop de análise
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
        
        # A) Espelhamento
        if use_mirror:
            final_clip = final_clip.with_effects([vfx.Mirrorx()])
            
        # B) Cores e Contraste (CORRIGIDO)
        if use_color:
            effects_list = []
            if brightness != 1.0:
                effects_list.append(vfx.MultiplyColor(brightness))
            if contrast != 1.0:
                # Aqui estava o erro: removemos o argumento 'contrast_thr'
                effects_list.append(vfx.LumContrast(lum=0, contrast=contrast))
            
            if effects_list:
                final_clip = final_clip.with_effects(effects_list)
            
        # C) Zoom/Crop
        if use_zoom:
            final_clip = apply_zoom_crop(final_clip, intensity=zoom_intensity)

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

        # 4. RENDERIZAÇÃO (MODO ECONOMIA DE MEMÓRIA)
        status_text.text("💾 4/4: Renderizando... (Modo Single-Thread para não travar)")
        
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
        
        # MUDANÇAS CRUCIAIS AQUI:
        # threads=1: Obriga a usar só 1 núcleo. É mais lento, mas gasta MUITO menos RAM.
        # preset='superfast': Troca qualidade de compressão por velocidade e menos memória.
        final_clip.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            preset='superfast', 
            threads=1,          # O SEGREDO: Reduzir para 1 evita o estouro de memória (502)
            logger=None
        )
        
        # Limpeza explícita de memória
        final_clip.close()
        video.close()
        del final_clip
        del video
        del audio
        
        bar.progress(100)
        
# --- FRONTEND ---
uploaded_file = st.file_uploader("Envie seu vídeo (.mp4)", type=["mp4"])

if uploaded_file is not None:
    st.video(uploaded_file)
    
    suffix = random.randint(1000, 9999)
    original_name = os.path.splitext(uploaded_file.name)[0]
    output_name = f"{original_name}_new_{suffix}.mp4"
    
    if st.button("🛡️ GERAR NOVO VÍDEO ÚNICO", type="primary"):
        with st.spinner('Processando...'):
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
