import streamlit as st
import tempfile
import os
from moviepy.editor import VideoFileClip, concatenate_videoclips, vfx, CompositeAudioClip, AudioArrayClip
import moviepy.audio.fx.all as afx
import numpy as np

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Blindador PRO Anti-IA", page_icon="🛡️", layout="centered")

st.title("🛡️ Blindagem de Vídeo (Nível Hard)")
st.markdown("""
Esta ferramenta aplica 3 camadas de proteção contra detecção de conteúdo:
1. **Truncagem Temporal:** Remove respirações e pausas.
2. **Camuflagem Espectral:** Injeta ruído branco imperceptível (Noise Floor).
3. **Filtro de Frequência:** Remove impressões digitais de áudio (<100Hz e >8kHz).
""")

# --- CONTROLES LATERAIS ---
st.sidebar.header("🎛️ Configurações")

st.sidebar.subheader("1. Corte de Silêncio")
threshold = st.sidebar.slider("Sensibilidade (Threshold)", 0.01, 0.10, 0.03, 0.005, help="Menor = Mais cortes.")
chunk_len = st.sidebar.slider("Resolução (s)", 0.01, 0.10, 0.05)

st.sidebar.subheader("2. Camadas Extras")
use_noise = st.sidebar.checkbox("Injetar Ruído Branco (-50dB)", value=True)
use_eq = st.sidebar.checkbox("Aplicar Equalização Anti-IA", value=True)
use_speed = st.sidebar.checkbox("Aceleração (1.05x)", value=True)

# --- FUNÇÃO GERADORA DE RUÍDO ---
def generate_noise(duration, fps=44100, volume=0.01):
    # Gera ruído branco aleatório
    # volume 0.01 é aprox -40dB a -50dB dependendo da normalização
    noise = np.random.uniform(-volume, volume, (int(duration * fps), 2))
    return AudioArrayClip(noise, fps=fps)

# --- PROCESSAMENTO PRINCIPAL ---
def process_video(uploaded_file):
    # Salvar arquivo temporário de entrada
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile.write(uploaded_file.read())
    
    status_text = st.empty()
    bar = st.progress(0)
    
    try:
        video = VideoFileClip(tfile.name)
        audio = video.audio
        
        # 1. ANÁLISE DE SILÊNCIO
        status_text.text("🔍 1/4: Mapeando silêncios...")
        intervals = []
        speaking = False
        start_time = 0
        
        # Percorre o áudio
        for i, t in enumerate(np.arange(0, audio.duration, chunk_len)):
            chunk = audio.subclip(t, min(t + chunk_len, audio.duration))
            if chunk.max_volume() >= threshold:
                if not speaking:
                    speaking = True
                    start_time = t
            else:
                if speaking:
                    speaking = False
                    intervals.append((max(0, start_time - 0.02), min(t + 0.02, audio.duration)))
            
            if i % 20 == 0: 
                bar.progress(min(30, int((t/audio.duration)*30)))

        if speaking:
            intervals.append((start_time, audio.duration))
            
        if not intervals:
            return None, "Erro: Nenhum áudio detectado acima do limite."

        # 2. CORTE E CONCATENAÇÃO
        status_text.text(f"✂️ 2/4: Removendo pausas ({len(intervals)} cortes)...")
        clips = [video.subclip(start, end) for start, end in intervals]
        final_clip = concatenate_videoclips(clips)
        bar.progress(50)

        # 3. ACELERAÇÃO
        if use_speed:
            final_clip = final_clip.fx(vfx.speedx, 1.05)

        # 4. ENGENHARIA DE ÁUDIO (EQ + RUÍDO)
        status_text.text("🎚️ 3/4: Aplicando blindagem de áudio...")
        
        current_audio = final_clip.audio
        
        # A) Equalização (Corta graves e super-agudos)
        if use_eq:
            # Highpass: Remove < 100Hz (zumbidos graves)
            # Lowpass: Remove > 8000Hz (agudos cristalinos)
            # Nota: Isso altera levemente a qualidade, parecendo 'rádio', o que é bom para anti-IA
            current_audio = current_audio.fx(afx.audio_filter, filter_name="highpass", f=100)
            current_audio = current_audio.fx(afx.audio_filter, filter_name="lowpass", f=8000)
        
        # B) Injeção de Ruído (Noise Floor)
        if use_noise:
            # Gera um clipe de estática do tamanho exato do vídeo final
            noise_clip = generate_noise(final_clip.duration, fps=44100, volume=0.005) # 0.005 é bem sutil
            # Mistura o áudio original com o ruído
            current_audio = CompositeAudioClip([current_audio, noise_clip])
            
        # Reaplica o áudio tratado ao vídeo
        final_clip.audio = current_audio
        bar.progress(70)

        # 5. RENDERIZAÇÃO
        status_text.text("💾 4/4: Renderizando vídeo final (Isso usa CPU)...")
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
        status_text.text("✅ Vídeo Blindado e Pronto!")
        
        video.close()
        return output_path, None

    except Exception as e:
        return None, str(e)

# --- FRONTEND ---
uploaded_file = st.file_uploader("Envie seu vídeo (.mp4)", type=["mp4"])

if uploaded_file is not None:
    st.video(uploaded_file)
    st.write(f"Tamanho original: {uploaded_file.size / 1e6:.2f} MB")
    
    if st.button("🛡️ INICIAR BLINDAGEM COMPLETA", type="primary"):
        with st.spinner('O Agente está processando... mantenha a aba aberta.'):
            result_path, error = process_video(uploaded_file)
            
            if error:
                st.error(error)
            else:
                st.success("Processo finalizado!")
                with open(result_path, "rb") as f:
                    st.download_button(
                        label="⬇️ BAIXAR VÍDEO FINAL",
                        data=f,
                        file_name="video_blindado_pro.mp4",
                        mime="video/mp4"
                    )
