const textInput = document.getElementById("textInput");
const charCount = document.getElementById("charCount");
const wordCount = document.getElementById("wordCount");
const generateBtn = document.getElementById("generateBtn");
const clearBtn = document.getElementById("clearBtn");
const pasteBtn = document.getElementById("pasteBtn");
const speed = document.getElementById("speed");
const speedValue = document.getElementById("speedValue");
const expression = document.getElementById("expression");
const expressionValue = document.getElementById("expressionValue");
const languageSelect = document.getElementById("language");

// Voice dropdown elements
const voiceSelectorDropdown = document.getElementById("voiceSelectorDropdown");
const voiceDropdownList = document.getElementById("voiceDropdown");
const selectedVoiceAvatar = document.getElementById("selectedVoiceAvatar");
const selectedVoiceName = document.getElementById("selectedVoiceName");
const selectedVoiceMeta = document.getElementById("selectedVoiceMeta");

// Result elements
const resultSection = document.getElementById("resultSection");
const resultTimeBadge = document.getElementById("resultTimeBadge");
const playBtn = document.getElementById("playBtn");
const audioDurationText = document.getElementById("audioDuration");
const downloadMp3Btn = document.getElementById("downloadMp3");
const downloadWavBtn = document.getElementById("downloadWav");
const regenerateBtn = document.getElementById("regenerateBtn");
const waveformContainer = document.getElementById("waveform");

// --- Pronunciation Lab ---
const vdPronunciationText = document.getElementById("vdPronunciationText");
const vdPronounceBtn = document.getElementById("vdPronounceBtn");
const vdPronounceResult = document.getElementById("vdPronounceResult");
const vdPronouncePlayBtn = document.getElementById("vdPronouncePlayBtn");
const vdPronounceOriginal = document.getElementById("vdPronounceOriginal");
const vdPronounceSayAs = document.getElementById("vdPronounceSayAs");
const vdAddPronunciationBtn = document.getElementById("vdAddPronunciationBtn");

let wavesurfer = null;
let currentVoices = [];
let selectedVoiceId = "meera";

let vdPronounceWavesurfer = null;
let currentPronounceAudio = null;

vdPronounceBtn.addEventListener("click", async () => {
  const text = vdPronunciationText.value.trim();
  if (!text) return;
  
  const originalText = vdPronounceBtn.textContent;
  vdPronounceBtn.textContent = "Generating...";
  vdPronounceBtn.disabled = true;
  
  try {
    const result = await generateSpeech({
      voice: activeVoiceDetails.id,
      input: text,
      language: activeVoiceDetails.languages[0],
      format: "mp3",
      model: "hindi-natural-v1"
    });
    
    vdPronounceResult.style.display = "block";
    
    if (vdPronounceWavesurfer) {
      vdPronounceWavesurfer.destroy();
    }
    
    vdPronounceWavesurfer = WaveSurfer.create({
      container: '#vdPronounceWaveform',
      waveColor: '#3a3d48', progressColor: '#8b5cf6',
      cursorColor: '#f8fafc', barWidth: 2, height: 36
    });
    
    vdPronounceWavesurfer.load(result.audio_url);
    
    vdPronouncePlayBtn.onclick = () => {
      vdPronounceWavesurfer.playPause();
      vdPronouncePlayBtn.textContent = vdPronounceWavesurfer.isPlaying() ? '⏸' : '▶';
    };
    
    vdPronounceWavesurfer.on('finish', () => {
      vdPronouncePlayBtn.textContent = '▶';
    });
    
  } catch (err) {
    console.error(err);
    alert("Generation failed");
  } finally {
    vdPronounceBtn.textContent = originalText;
    vdPronounceBtn.disabled = false;
  }
});

vdAddPronunciationBtn.addEventListener("click", async () => {
  const original = vdPronounceOriginal.value.trim();
  const sayAs = vdPronounceSayAs.value.trim();
  if (!original || !sayAs) return;
  
  const originalText = vdAddPronunciationBtn.textContent;
  vdAddPronunciationBtn.textContent = "Adding...";
  vdAddPronunciationBtn.disabled = true;
  
  try {
    await addPronunciation(original, sayAs);
    vdAddPronunciationBtn.textContent = "Added!";
    vdPronounceOriginal.value = "";
    vdPronounceSayAs.value = "";
    setTimeout(() => {
      vdAddPronunciationBtn.textContent = originalText;
      vdAddPronunciationBtn.disabled = false;
    }, 2000);
  } catch (err) {
    console.error(err);
    vdAddPronunciationBtn.textContent = "Error";
    setTimeout(() => {
      vdAddPronunciationBtn.textContent = originalText;
      vdAddPronunciationBtn.disabled = false;
    }, 2000);
  }
});

// Initialize WaveSurfer
function initWaveSurfer() {
  if (wavesurfer) {
    wavesurfer.destroy();
  }
  
  wavesurfer = WaveSurfer.create({
    container: '#waveform',
    waveColor: '#3a3d48',
    progressColor: '#8b5cf6',
    cursorColor: '#f8fafc',
    barWidth: 3,
    barRadius: 3,
    cursorWidth: 2,
    height: 40,
    barGap: 3
  });
  
  wavesurfer.on('ready', () => {
    const duration = wavesurfer.getDuration();
    audioDurationText.textContent = formatTime(duration);
    wavesurfer.setPlaybackRate(Number(speed.value));
  });
  
  wavesurfer.on('audioprocess', () => {
    const time = wavesurfer.getCurrentTime();
    audioDurationText.textContent = formatTime(time);
  });
  
  wavesurfer.on('finish', () => {
    playBtn.textContent = '▶';
    audioDurationText.textContent = formatTime(wavesurfer.getDuration());
  });
}

function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

// Counters
function updateCounters() {
  const text = textInput.value.trim();
  charCount.textContent = textInput.value.length.toLocaleString();
  wordCount.textContent = text ? text.split(/\s+/).length : 0;
}

textInput.addEventListener("input", updateCounters);

speed.addEventListener("input", () => {
  const val = Number(speed.value);
  speedValue.textContent = `${val.toFixed(1)}×`;
  if (wavesurfer) {
    wavesurfer.setPlaybackRate(val);
  }
});

expression.addEventListener("input", () => {
  expressionValue.textContent = `${expression.value}%`;
});

clearBtn.addEventListener("click", () => {
  textInput.value = "";
  updateCounters();
  textInput.focus();
});

pasteBtn.addEventListener("click", async () => {
  try {
    const text = await navigator.clipboard.readText();
    textInput.value += text;
    updateCounters();
  } catch {
    alert("Clipboard permission denied.");
  }
});

// Voice selection dropdown
voiceSelectorDropdown.addEventListener("click", () => {
  const isVisible = voiceDropdownList.style.display === "block";
  voiceDropdownList.style.display = isVisible ? "none" : "block";
});

// Close dropdown if clicking outside
document.addEventListener("click", (e) => {
  if (!voiceSelectorDropdown.contains(e.target) && !voiceDropdownList.contains(e.target)) {
    voiceDropdownList.style.display = "none";
  }
});

function selectVoice(voiceId) {
  const voice = currentVoices.find(v => v.id === voiceId);
  if (!voice) return;
  
  selectedVoiceId = voice.id;
  selectedVoiceAvatar.textContent = voice.name.charAt(0).toUpperCase();
  selectedVoiceName.textContent = voice.name;
  
  const langs = voice.languages ? voice.languages.map(l => l.toUpperCase()).join(", ") : "";
  const primaryStyle = voice.styles && voice.styles.length > 0 ? voice.styles[0] : "General";
  const styleStr = primaryStyle.charAt(0).toUpperCase() + primaryStyle.slice(1);
  const genderStr = voice.gender ? voice.gender.charAt(0).toUpperCase() + voice.gender.slice(1) : "";
  
  selectedVoiceMeta.textContent = `${langs} · ${styleStr} · ${genderStr}`;
  voiceDropdownList.style.display = "none";
}

// Load voices
async function loadVoices() {
  try {
    const data = await getVoices();
    currentVoices = data.voices || [];
    
    voiceDropdownList.innerHTML = "";
    
    currentVoices.forEach(voice => {
      const option = document.createElement("div");
      option.className = "voice-option";
      
      const langs = voice.languages ? voice.languages.map(l => l.toUpperCase()).join(", ") : "";
      const primaryStyle = voice.styles && voice.styles.length > 0 ? voice.styles[0] : "General";
      const styleStr = primaryStyle.charAt(0).toUpperCase() + primaryStyle.slice(1);
      const genderStr = voice.gender ? voice.gender.charAt(0).toUpperCase() + voice.gender.slice(1) : "";
      
      option.innerHTML = `
        <div class="voice-avatar">${voice.name.charAt(0).toUpperCase()}</div>
        <div class="voice-info">
          <strong>${voice.name}</strong>
          <small>${langs} · ${styleStr} · ${genderStr}</small>
        </div>
      `;
      
      option.addEventListener("click", () => selectVoice(voice.id));
      voiceDropdownList.appendChild(option);
    });
    
    if (currentVoices.length > 0) {
      // Default select Meera or the first one
      const defaultVoice = currentVoices.find(v => v.id === "meera") || currentVoices[0];
      selectVoice(defaultVoice.id);
    }
  } catch (err) {
    console.error("Failed to load voices", err);
    selectedVoiceName.textContent = "Error loading voices";
    selectedVoiceMeta.textContent = "";
  }
}

// Play button logic
playBtn.addEventListener('click', () => {
  if (!wavesurfer) return;
  if (wavesurfer.isPlaying()) {
    wavesurfer.pause();
    playBtn.textContent = '▶';
  } else {
    wavesurfer.play();
    playBtn.textContent = '⏸';
  }
});

// Delete logic for current result
const deleteBtn = document.getElementById("deleteBtn");
let currentAudioId = null;

deleteBtn.addEventListener("click", async () => {
  if (!currentAudioId) return;
  if (!confirm("Are you sure you want to delete this audio?")) return;
  
  deleteBtn.disabled = true;
  try {
    await deleteAudio(currentAudioId);
    resultSection.style.display = "none";
    if (wavesurfer) {
      wavesurfer.destroy();
      wavesurfer = null;
    }
    loadHistoryView(); // Refresh history
  } catch (err) {
    alert("Failed to delete: " + err.message);
  } finally {
    deleteBtn.disabled = false;
  }
});

// Generate
async function handleGenerate() {
  const text = textInput.value.trim();
  if (!text) {
    alert("Please enter some text.");
    return;
  }
  
  generateBtn.disabled = true;
  generateBtn.innerHTML = "<span>◌</span> Generating... 0%";
  
  // Estimate time based on text length (approx 0.15s per character for XTTS)
  const estimatedSeconds = Math.max(3, Math.floor(text.length * 0.15));
  let progress = 0;
  
  const progressInterval = setInterval(() => {
    // Easing function: slows down as it approaches 99%
    const remaining = 99 - progress;
    progress += Math.max(1, Math.floor(remaining * 0.05));
    if (progress > 99) progress = 99;
    
    generateBtn.innerHTML = `<span>◌</span> Generating... ${progress}%`;
  }, (estimatedSeconds * 1000) / 30); // 30 updates over the estimated time
  
  try {
    const result = await generateSpeech({
      voice: selectedVoiceId,
      input: text,
      language: languageSelect.value,
      format: "mp3",
      model: "hindi-natural-v1"
    });
    
    currentAudioId = result.id;
    
    // Show results
    resultSection.style.display = "block";
    resultTimeBadge.textContent = result.cached ? "⚡ Cached" : "Just now";
    
    // Setup WaveSurfer
    initWaveSurfer();
    
    // Since API sends back /audio/single/..., update download links
    downloadMp3Btn.href = result.audio_url;
    downloadMp3Btn.download = `voxai_${selectedVoiceId}_${Date.now()}.mp3`;
    downloadWavBtn.href = result.audio_url.replace(".mp3", ".wav");
    downloadWavBtn.download = `voxai_${selectedVoiceId}_${Date.now()}.wav`;
    
    // Load audio into WaveSurfer
    wavesurfer.load(result.audio_url);
    
    // Reset play button
    playBtn.textContent = '▶';
    
    // Scroll to results
    resultSection.scrollIntoView({ behavior: 'smooth' });

  } catch (error) {
    alert(error.message);
  } finally {
    clearInterval(progressInterval);
    generateBtn.disabled = false;
    generateBtn.innerHTML = "<span>✦</span> Generate speech";
  }
}

generateBtn.addEventListener("click", handleGenerate);
regenerateBtn.addEventListener("click", handleGenerate);

document.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    generateBtn.click();
  }
});

// Routing / Tabs
const studioView = document.getElementById("studioView");
const voicesView = document.getElementById("voicesView");
const historyView = document.getElementById("historyView");
const createVoiceView = document.getElementById("createVoiceView");

const navStudio = document.getElementById("navStudio");
const navVoices = document.getElementById("navVoices");
const navHistory = document.getElementById("navHistory");
const navCreateVoice = document.getElementById("navCreateVoice");
const navPronunciations = document.getElementById("navPronunciations");

function switchTab(tabName) {
  navStudio.classList.remove("active");
  navVoices.classList.remove("active");
  navHistory.classList.remove("active");
  if(navCreateVoice) navCreateVoice.classList.remove("active");
  if(navPronunciations) navPronunciations.classList.remove("active");
  
  studioView.style.display = "none";
  voicesView.style.display = "none";
  historyView.style.display = "none";
  if(createVoiceView) createVoiceView.style.display = "none";
  const pronView = document.getElementById("pronunciationsView");
  if(pronView) pronView.style.display = "none";
  
  if (tabName === "Studio") {
    navStudio.classList.add("active");
    studioView.style.display = "block";
  } else if (tabName === "Voices") {
    navVoices.classList.add("active");
    voicesView.style.display = "block";
    renderVoiceGrid();
  } else if (tabName === "History") {
    navHistory.classList.add("active");
    historyView.style.display = "block";
    loadHistoryView();
  } else if (tabName === "CreateVoice") {
    navCreateVoice.classList.add("active");
    createVoiceView.style.display = "block";
  } else if (tabName === "Pronunciations") {
    if(navPronunciations) navPronunciations.classList.add("active");
    if(pronView) pronView.style.display = "block";
    loadPronunciations();
  }
}

navStudio.addEventListener("click", () => switchTab("Studio"));
navVoices.addEventListener("click", () => switchTab("Voices"));
navHistory.addEventListener("click", () => switchTab("History"));
if (navCreateVoice) navCreateVoice.addEventListener("click", () => switchTab("CreateVoice"));
if (navPronunciations) navPronunciations.addEventListener("click", () => switchTab("Pronunciations"));


// Voice Library Grid & Filtering
const voicesGrid = document.getElementById("voicesGrid");
const filterLangs = document.querySelectorAll(".voice-filter-lang");
const filterGenders = document.querySelectorAll(".voice-filter-gender");
const filterTags = document.querySelectorAll(".voice-filter-tag");

function getActiveFilters(nodeList) {
  return Array.from(nodeList).filter(cb => cb.checked).map(cb => cb.value);
}

function renderVoiceGrid() {
  const activeLangs = getActiveFilters(filterLangs);
  const activeGenders = getActiveFilters(filterGenders);
  const activeTags = getActiveFilters(filterTags);
  
  const filtered = currentVoices.filter(v => {
    const matchLang = activeLangs.length === 0 || activeLangs.some(l => v.languages.includes(l));
    const matchGender = activeGenders.length === 0 || activeGenders.includes(v.gender) || v.gender === "unknown";
    const matchTag = activeTags.length === 0 || activeTags.some(t => v.styles.includes(t) || v.tags.map(tag=>tag.toLowerCase()).includes(t));
    return matchLang && matchGender && matchTag;
  });
  
  voicesGrid.innerHTML = "";
  
  if (filtered.length === 0) {
    voicesGrid.innerHTML = "<div style='grid-column: 1/-1; color: var(--muted); text-align: center; padding: 40px;'>No voices match your filters.</div>";
    return;
  }
  
  filtered.forEach(voice => {
    const langs = voice.languages.map(l => l.toUpperCase()).join(", ");
    const gender = voice.gender.charAt(0).toUpperCase() + voice.gender.slice(1);
    const primaryTag = voice.styles[0] ? voice.styles[0].charAt(0).toUpperCase() + voice.styles[0].slice(1) : "";
    
    // Status indicator
    const statusDot = voice.production ? '<span style="color: #10b981;">●</span>' : '<span style="color: #fbbf24;">●</span>';
    
    const card = document.createElement("div");
    card.className = "voice-card";
    card.onclick = (e) => {
      // Don't open panel if clicking preview button
      if (e.target.closest('.vc-preview')) return;
      openVoiceStudio(voice);
    };
    
    card.innerHTML = `
      <div class="vc-header">
        <div class="vc-avatar">${voice.name.charAt(0).toUpperCase()}</div>
        <div class="vc-info">
          <h3>${voice.name} ${statusDot}</h3>
          <p>${gender} · ${langs} · ${primaryTag}</p>
        </div>
      </div>
      <div class="vc-tags">
        ${voice.tags.slice(0, 3).map(t => `<span class="vc-tag">${t}</span>`).join('')}
      </div>
      <div style="display: flex; gap: 8px; margin-top: auto;">
        <div class="vc-preview" style="flex: 1;" onclick="playCardPreview('${voice.preview}')">
          <span>▶</span> <span style="font-size: 11px;">Preview</span>
        </div>
        <div class="vc-preview" style="padding: 6px 12px; flex: 0; display: flex; align-items: center; justify-content: center; color: #ef4444; border-color: rgba(239, 68, 68, 0.2);" onclick="deleteVoiceCard('${voice.id}', event)">
          <span style="font-size: 14px;">🗑</span>
        </div>
      </div>
    `;
    
    voicesGrid.appendChild(card);
  });
}

// Global delete voice handler
window.deleteVoiceCard = async function(voiceId, event) {
  // Prevent the card click from opening the side panel
  event.stopPropagation();
  
  if (!confirm("Are you sure you want to permanently delete this voice?")) return;
  
  try {
    await deleteVoice(voiceId);
    // Reload voices and re-render grid
    await loadVoices();
    renderVoiceGrid();
  } catch (err) {
    alert("Failed to delete voice: " + err.message);
  }
};

// Add event listeners to filters to re-render
[...filterLangs, ...filterGenders, ...filterTags].forEach(cb => {
  cb.addEventListener('change', renderVoiceGrid);
});

// Play audio directly from card
let currentCardAudio = null;
window.playCardPreview = function(url) {
  if (currentCardAudio) {
    currentCardAudio.pause();
  }
  currentCardAudio = new Audio(url);
  currentCardAudio.play();
};

// Voice Details Side Panel
const vdBackdrop = document.getElementById("voiceDetailsBackdrop");
const vdPanel = document.getElementById("voiceDetailsPanel");
const closeVd = document.getElementById("closeVoiceDetails");

let activeVoiceDetails = null;
let vdPreviewWavesurfer = null;
let vdTestWavesurfer = null;

function openVoiceDetails(voice) {
  activeVoiceDetails = voice;
  document.getElementById("vdAvatar").textContent = voice.name.charAt(0).toUpperCase();
  document.getElementById("vdName").textContent = voice.name;
  
  const langs = voice.languages.map(l => l.toUpperCase()).join(", ");
  const gender = voice.gender.charAt(0).toUpperCase() + voice.gender.slice(1);
  const primaryTag = voice.styles[0] ? voice.styles[0].charAt(0).toUpperCase() + voice.styles[0].slice(1) : "";
  document.getElementById("vdMeta").textContent = `${gender} · ${langs} · ${primaryTag}`;
  
  document.getElementById("vdTags").innerHTML = voice.tags.map(t => `<span class="vc-tag">${t}</span>`).join('');
  
  // Setup Preview WaveSurfer
  if (vdPreviewWavesurfer) vdPreviewWavesurfer.destroy();
  vdPreviewWavesurfer = WaveSurfer.create({
    container: '#vdPreviewWaveform',
    waveColor: '#3a3d48', progressColor: '#8b5cf6',
    cursorColor: '#f8fafc', barWidth: 2, height: 36
  });
  vdPreviewWavesurfer.load(voice.preview);
  document.getElementById("vdPreviewPlayBtn").onclick = () => vdPreviewWavesurfer.playPause();
  vdPreviewWavesurfer.on('finish', () => { document.getElementById("vdPreviewPlayBtn").textContent = "▶"; });
  vdPreviewWavesurfer.on('play', () => { document.getElementById("vdPreviewPlayBtn").textContent = "⏸"; });
  vdPreviewWavesurfer.on('pause', () => { document.getElementById("vdPreviewPlayBtn").textContent = "▶"; });
  vdPreviewWavesurfer.on('ready', () => {
    document.getElementById("vdPreviewDuration").textContent = formatTime(vdPreviewWavesurfer.getDuration());
  });

  // Reset test/pronounce sections
  document.getElementById("vdTestResult").style.display = "none";
  document.getElementById("vdTestText").value = "";
  document.getElementById("vdPronounceResult").style.display = "none";
  document.getElementById("vdPronunciationText").value = "";
  
  vdBackdrop.classList.add("active");
  vdPanel.classList.add("active");
}

function closeVoiceDetails() {
  vdBackdrop.classList.remove("active");
  vdPanel.classList.remove("active");
  if (vdPreviewWavesurfer) vdPreviewWavesurfer.pause();
  if (vdTestWavesurfer) vdTestWavesurfer.pause();
  if (vdPronounceWavesurfer) vdPronounceWavesurfer.pause();
  if (currentCardAudio) currentCardAudio.pause();
}

closeVd.addEventListener("click", closeVoiceDetails);
vdBackdrop.addEventListener("click", closeVoiceDetails);

document.getElementById("vdUseVoiceBtn").addEventListener("click", () => {
  if (activeVoiceDetails) {
    selectVoice(activeVoiceDetails.id);
    closeVoiceDetails();
    switchTab("Studio");
  }
});

// Live Testing in panel
document.getElementById("vdGenerateTestBtn").addEventListener("click", async () => {
  const text = document.getElementById("vdTestText").value.trim();
  if (!text) return;
  
  const btn = document.getElementById("vdGenerateTestBtn");
  btn.disabled = true;
  btn.textContent = "Generating...";
  
  try {
    const result = await generateSpeech({
      voice: activeVoiceDetails.id,
      input: text,
      language: activeVoiceDetails.languages[0],
      format: "mp3",
      model: "hindi-natural-v1"
    });
    
    document.getElementById("vdTestResult").style.display = "block";
    
    if (vdTestWavesurfer) vdTestWavesurfer.destroy();
    vdTestWavesurfer = WaveSurfer.create({
      container: '#vdTestWaveform',
      waveColor: '#3a3d48', progressColor: '#8b5cf6',
      cursorColor: '#f8fafc', barWidth: 2, height: 36
    });
    
    vdTestWavesurfer.load(result.audio_url);
    const playBtn = document.getElementById("vdTestPlayBtn");
    playBtn.onclick = () => vdTestWavesurfer.playPause();
    vdTestWavesurfer.on('finish', () => { playBtn.textContent = "▶"; });
    vdTestWavesurfer.on('play', () => { playBtn.textContent = "⏸"; });
    vdTestWavesurfer.on('pause', () => { playBtn.textContent = "▶"; });
    
  } catch(e) {
    alert("Test generation failed.");
  } finally {
    btn.disabled = false;
    btn.textContent = "✦ Generate Preview";
  }
});

// Pronunciation Lab in panel
document.getElementById("vdPronounceBtn").addEventListener("click", async () => {
  const text = document.getElementById("vdPronunciationText").value.trim();
  if (!text) return;
  
  const btn = document.getElementById("vdPronounceBtn");
  btn.disabled = true;
  btn.textContent = "Generating...";
  
  try {
    const result = await generateSpeech({
      voice: activeVoiceDetails.id,
      input: text,
      language: activeVoiceDetails.languages[0],
      format: "mp3",
      model: "hindi-natural-v1"
    });
    
    document.getElementById("vdPronounceResult").style.display = "block";
    
    if (vdPronounceWavesurfer) vdPronounceWavesurfer.destroy();
    vdPronounceWavesurfer = WaveSurfer.create({
      container: '#vdPronounceWaveform',
      waveColor: '#3a3d48', progressColor: '#8b5cf6',
      cursorColor: '#f8fafc', barWidth: 2, height: 36
    });
    
    vdPronounceWavesurfer.load(result.audio_url);
    const playBtn = document.getElementById("vdPronouncePlayBtn");
    playBtn.onclick = () => vdPronounceWavesurfer.playPause();
    vdPronounceWavesurfer.on('finish', () => { playBtn.textContent = "▶"; });
    vdPronounceWavesurfer.on('play', () => { playBtn.textContent = "⏸"; });
    vdPronounceWavesurfer.on('pause', () => { playBtn.textContent = "▶"; });
    
  } catch(e) {
    alert("Pronunciation generation failed.");
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate";
  }
});

// History view logic
const historyList = document.getElementById("historyList");

async function loadHistoryView() {
  historyList.innerHTML = "<div class='history-empty'>Loading history...</div>";
  try {
    const data = await getHistory();
    const history = data.history || [];
    
    if (history.length === 0) {
      historyList.innerHTML = "<div class='history-empty'>No generation history found.</div>";
      return;
    }
    
    historyList.innerHTML = "";
    
    history.forEach(item => {
      const date = new Date(item.created_at * 1000).toLocaleString();
      const div = document.createElement("div");
      div.className = "history-item";
      div.id = `history-item-${item.id}`;
      
      div.innerHTML = `
        <div class="history-item-left">
          <div class="history-avatar">${item.voice.charAt(0).toUpperCase()}</div>
          <div class="history-info">
            <strong>${item.voice}</strong>
            <div class="history-text">"${item.text.replace(/\n/g, '<br>')}"</div>
            <div class="history-time">${date}</div>
          </div>
        </div>
        <div class="history-actions">
          <audio controls src="${item.audio_url}" style="width: 100%; max-width: 280px;"></audio>
          <div class="history-buttons">
            <button class="secondary-btn" onclick="reusePrompt('${encodeURIComponent(item.text).replace(/'/g, "%27")}', '${item.voice}')">✏️ Reuse</button>
            <a class="secondary-btn" href="${item.audio_url}" download="voxai_${item.voice}.mp3" style="text-decoration:none;">↓ Download</a>
            <button class="secondary-btn" style="color:#ef4444; border-color:rgba(239,68,68,0.3);" onclick="deleteHistoryItem('${item.id}')">🗑</button>
          </div>
        </div>
      `;
      historyList.appendChild(div);
    });
  } catch (err) {
    historyList.innerHTML = "<div class='history-empty'>Failed to load history</div>";
  }
}

// Global functions for inline HTML onclick handlers
window.reusePrompt = function(encodedText, voiceId) {
  const text = decodeURIComponent(encodedText);
  textInput.value = text;
  updateCounters();
  
  // Select the voice
  selectVoice(voiceId);
  
  // Switch to Studio tab
  switchTab("Studio");
  
  // Flash textarea briefly to show it changed
  textInput.style.backgroundColor = "rgba(139, 92, 246, 0.2)";
  setTimeout(() => {
    textInput.style.backgroundColor = "transparent";
  }, 300);
};

window.deleteHistoryItem = async function(id) {
  if (!confirm("Are you sure you want to delete this audio?")) return;
  try {
    await deleteAudio(id);
    
    // Check if it's currently loaded in Studio
    if (currentAudioId === id) {
      resultSection.style.display = "none";
      if (wavesurfer) {
        wavesurfer.destroy();
        wavesurfer = null;
      }
    }
    
    // Remove from UI instantly
    const el = document.getElementById(`history-item-${id}`);
    if (el) {
      el.style.opacity = '0';
      el.style.transform = 'scale(0.95)';
      el.style.transition = '0.3s';
      setTimeout(() => el.remove(), 300);
    }
    
  } catch (err) {
    alert("Failed to delete: " + err.message);
  }
};

// Init

initWaveSurfer();
loadVoices();

// --- Create Voice (Voice Cloning) Logic ---
const cvRecordBtn = document.getElementById("cvRecordBtn");
const cvTimer = document.getElementById("cvTimer");
const cvAudioPreview = document.getElementById("cvAudioPreview");
const cvName = document.getElementById("cvName");
const cvSubmitBtn = document.getElementById("cvSubmitBtn");

let mediaRecorder = null;
let audioChunks = [];
let recordInterval = null;
let recordTime = 0;
let recordedBlob = null;
let isRecording = false;

// WIZARD LOGIC
const wizStep1 = document.getElementById("wizStep1");
const wizStep2 = document.getElementById("wizStep2");
const wizStep3 = document.getElementById("wizStep3");

const wizContent1 = document.getElementById("wizardStep1Content");
const wizContent2 = document.getElementById("wizardStep2Content");
const wizContent3 = document.getElementById("wizardStep3Content");

const btnNextStep1 = document.getElementById("btnNextStep1");
const btnBackStep2 = document.getElementById("btnBackStep2");
const btnNextStep2 = document.getElementById("btnNextStep2");
const btnBackStep3 = document.getElementById("btnBackStep3");

function goToWizardStep(step) {
  wizContent1.style.display = step === 1 ? "block" : "none";
  wizContent2.style.display = step === 2 ? "block" : "none";
  wizContent3.style.display = step === 3 ? "block" : "none";
  
  wizStep1.classList.toggle("active", step === 1);
  wizStep1.style.color = step === 1 ? "var(--text)" : "var(--muted)";
  
  wizStep2.classList.toggle("active", step === 2);
  wizStep2.style.color = step === 2 ? "var(--text)" : "var(--muted)";
  
  wizStep3.classList.toggle("active", step === 3);
  wizStep3.style.color = step === 3 ? "var(--text)" : "var(--muted)";
}

btnNextStep1.addEventListener("click", () => {
  if (!recordedBlob) return alert("Please record some audio first.");
  goToWizardStep(2);
  
  // Simulate quality checking
  document.getElementById("qualityAnalyzing").style.display = "block";
  document.getElementById("qualityResults").style.display = "none";
  btnNextStep2.disabled = true;
  
  setTimeout(() => {
    document.getElementById("qualityAnalyzing").style.display = "none";
    document.getElementById("qualityResults").style.display = "block";
    btnNextStep2.disabled = false;
  }, 2000);
});

btnBackStep2.addEventListener("click", () => goToWizardStep(1));
btnNextStep2.addEventListener("click", () => goToWizardStep(3));
btnBackStep3.addEventListener("click", () => goToWizardStep(2));

// Record Logic
cvRecordBtn.addEventListener("click", async () => {
  if (isRecording) {
    if (mediaRecorder) mediaRecorder.stop();
    return;
  }
  
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    
    mediaRecorder.ondataavailable = e => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };
    
    mediaRecorder.onstop = () => {
      isRecording = false;
      clearInterval(recordInterval);
      cvRecordBtn.textContent = "Start recording";
      cvRecordBtn.classList.remove("recording-active");
      
      recordedBlob = new Blob(audioChunks, { type: 'audio/wav' });
      const audioUrl = URL.createObjectURL(recordedBlob);
      cvAudioPreview.src = audioUrl;
      cvAudioPreview.style.display = "block";
      
      stream.getTracks().forEach(track => track.stop());
    };
    
    mediaRecorder.start();
    isRecording = true;
    cvRecordBtn.textContent = "Stop recording";
    cvRecordBtn.classList.add("recording-active");
    
    recordTime = 0;
    cvTimer.textContent = "00:00"; // Unlimited up to 10 min typically, simplified here
    
    recordInterval = setInterval(() => {
      recordTime++;
      const m = Math.floor(recordTime / 60).toString().padStart(2, '0');
      const s = (recordTime % 60).toString().padStart(2, '0');
      cvTimer.textContent = `${m}:${s}`;
      
      if (recordTime >= 600) mediaRecorder.stop(); // auto stop at 10 mins
    }, 1000);
    
  } catch (err) {
    alert("Could not access microphone: " + err.message);
  }
});

cvSubmitBtn.addEventListener("click", async () => {
  const name = cvName.value.trim();
  if (!name) return alert("Please provide a voice name");
  
  const selectedLang = document.getElementById("cvLang").value;
  const profileName = document.getElementById("cvProfileName").value;
  
  const formData = new FormData();
  formData.append("audio", recordedBlob, "cloned_voice.wav");
  formData.append("name", name);
  formData.append("language", selectedLang);
  formData.append("profile", profileName); // New profile field
  
  cvSubmitBtn.disabled = true;
  cvSubmitBtn.textContent = "Creating Dataset & Voice...";
  
  try {
    const response = await fetch(`${API_BASE}/v1/voices/clone`, {
      method: "POST",
      body: formData
    });
    
    if (!response.ok) throw new Error("Failed to clone voice");
    
    alert(`Voice "${name}" created successfully!`);
    
    // Reset wizard
    cvName.value = "";
    cvAudioPreview.style.display = "none";
    recordedBlob = null;
    cvSubmitBtn.disabled = false;
    cvSubmitBtn.textContent = "Create Voice Profile";
    cvTimer.textContent = "00:00";
    goToWizardStep(1);
    
    await loadVoices();
    switchTab("Voices");
  } catch (err) {
    alert("Error: " + err.message);
    cvSubmitBtn.textContent = "Create Voice Profile";
    cvSubmitBtn.disabled = false;
  }
});


// PRONUNCIATIONS LOGIC
async function loadPronunciations() {
  const tbody = document.getElementById("pronTableBody");
  if (!tbody) return;
  tbody.innerHTML = "<tr><td colspan='4' style='padding: 16px; text-align: center; color: var(--muted);'>Loading...</td></tr>";
  
  try {
    const data = await getPronunciations();
    tbody.innerHTML = "";
    
    if (data.pronunciations.length === 0) {
      tbody.innerHTML = "<tr><td colspan='4' style='padding: 16px; text-align: center; color: var(--muted);'>No pronunciations added yet.</td></tr>";
      return;
    }
    
    data.pronunciations.forEach(p => {
      const tr = document.createElement("tr");
      tr.style.borderBottom = "1px solid var(--border)";
      tr.innerHTML = `
        <td style="padding: 12px 16px; font-weight: 500;">${p.original}</td>
        <td style="padding: 12px 16px; color: #10b981;">${p.say_as}</td>
        <td style="padding: 12px 16px;">
          <span style="background: rgba(139, 92, 246, 0.1); color: #8b5cf6; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem;">
            ${p.language.toUpperCase()}
          </span>
        </td>
        <td style="padding: 12px 16px;">
          <button class="delete-pron-btn" data-id="${p.id}" style="background: transparent; border: none; color: #ef4444; cursor: pointer;">🗑️</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
    
    document.querySelectorAll(".delete-pron-btn").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        const id = e.target.dataset.id;
        if (confirm("Delete this pronunciation?")) {
          await deletePronunciation(id);
          loadPronunciations();
        }
      });
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan='4' style='padding: 16px; color: #ef4444;'>Failed to load: ${err.message}</td></tr>`;
  }
}

const addPronBtn = document.getElementById("addPronBtn");
if (addPronBtn) {
  addPronBtn.addEventListener("click", async () => {
    const orig = document.getElementById("pronOriginal").value.trim();
    const say = document.getElementById("pronSayAs").value.trim();
    const lang = document.getElementById("pronLanguage").value;
    
    if (!orig || !say) return alert("Please fill in both original and say as fields.");
    
    addPronBtn.disabled = true;
    addPronBtn.textContent = "Adding...";
    
    try {
      await addPronunciation(orig, say, lang);
      document.getElementById("pronOriginal").value = "";
      document.getElementById("pronSayAs").value = "";
      loadPronunciations();
    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      addPronBtn.disabled = false;
      addPronBtn.textContent = "Add Word";
    }
  });
}