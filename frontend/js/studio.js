// VOICE STUDIO LOGIC

let activeStudioVoice = null;
let vsPreviewWaveSurfer = null;
let vsCompareWaveA = null;
let vsCompareWaveB = null;

let currentSettings = {};
let comparisonSettingsA = null;

const vsOverlay = document.getElementById("voiceStudioOverlay");
const vsPanel = document.getElementById("voiceStudioPanel");

// Initialize WaveSurfers
function initStudioWaveSurfers() {
  if (!vsPreviewWaveSurfer) {
    vsPreviewWaveSurfer = WaveSurfer.create({
      container: '#vsWaveform', waveColor: '#3a3d48', progressColor: '#8b5cf6',
      cursorColor: '#f8fafc', barWidth: 2, height: 30
    });
    vsPreviewWaveSurfer.on('finish', () => { document.getElementById("vsPlayBtn").textContent = "▶"; });
    vsPreviewWaveSurfer.on('play', () => { document.getElementById("vsPlayBtn").textContent = "⏸"; });
    vsPreviewWaveSurfer.on('pause', () => { document.getElementById("vsPlayBtn").textContent = "▶"; });
    document.getElementById("vsPlayBtn").onclick = () => vsPreviewWaveSurfer.playPause();
  }
  
  if (!vsCompareWaveA) {
    vsCompareWaveA = WaveSurfer.create({
      container: '#vsWaveA', waveColor: '#3a3d48', progressColor: '#10b981',
      cursorColor: '#f8fafc', barWidth: 2, height: 30
    });
    document.getElementById("vsPlayA").onclick = () => vsCompareWaveA.playPause();
    vsCompareWaveA.on('play', () => { document.getElementById("vsPlayA").textContent = "⏸"; });
    vsCompareWaveA.on('pause', () => { document.getElementById("vsPlayA").textContent = "▶"; });
    vsCompareWaveA.on('finish', () => { document.getElementById("vsPlayA").textContent = "▶"; });
  }
  
  if (!vsCompareWaveB) {
    vsCompareWaveB = WaveSurfer.create({
      container: '#vsWaveB', waveColor: '#3a3d48', progressColor: '#ef4444',
      cursorColor: '#f8fafc', barWidth: 2, height: 30
    });
    document.getElementById("vsPlayB").onclick = () => vsCompareWaveB.playPause();
    vsCompareWaveB.on('play', () => { document.getElementById("vsPlayB").textContent = "⏸"; });
    vsCompareWaveB.on('pause', () => { document.getElementById("vsPlayB").textContent = "▶"; });
    vsCompareWaveB.on('finish', () => { document.getElementById("vsPlayB").textContent = "▶"; });
  }
}

// Tab Switching
document.querySelectorAll('.vs-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.vs-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.vs-tab-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(tab.dataset.tab).classList.add('active');
  });
});

async function openVoiceStudio(voice) {
  activeStudioVoice = voice;
  initStudioWaveSurfers();
  
  document.getElementById("vsAvatar").textContent = voice.name.charAt(0).toUpperCase();
  document.getElementById("vsName").textContent = voice.name;
  
  const langs = voice.languages ? voice.languages.map(l => l.toUpperCase()).join(", ") : "";
  document.getElementById("vsMeta").textContent = `${voice.engine} · ${langs}`;
  
  document.getElementById("vsAudioResult").style.display = "none";
  document.getElementById("vsCompareResult").style.display = "none";
  vsPreviewWaveSurfer.empty();
  
  // Handle capabilities
  const caps = voice.capabilities || {};
  document.getElementById("ctrl-stability").style.display = caps.stability ? "block" : "none";
  document.getElementById("ctrl-similarity").style.display = caps.similarity ? "block" : "none";
  document.getElementById("ctrl-expressiveness").style.display = caps.expressiveness ? "block" : "none";
  
  // Load Default Settings
  try {
    currentSettings = await getVoiceSettings(voice.id);
    updateStudioSliders(currentSettings);
    loadVoiceVersions();
  } catch (e) {
    console.error("Could not load settings", e);
  }
  
  // Reset Macros
  document.getElementById("inp-age").value = 50;
  document.getElementById("inp-personality").value = 50;
  document.getElementById("inp-authority").value = 50;
  
  // Switch to first tab
  document.querySelector('.vs-tab[data-tab="tab-character"]').click();
  
  vsOverlay.classList.add("active");
  vsPanel.classList.add("active");
}

function updateStudioSliders(s) {
  const setVal = (id, val, textFn) => {
    const el = document.getElementById(id);
    if (el && val !== undefined) {
      el.value = val;
      const valEl = document.getElementById(id.replace("inp-", "val-"));
      if (valEl) valEl.textContent = textFn ? textFn(val) : val;
    }
  };
  
  setVal("inp-speed", s.speed, v => Number(v).toFixed(2) + "×");
  setVal("inp-pitch", s.pitch, v => Number(v).toFixed(1));
  setVal("inp-stability", s.stability ? s.stability * 100 : 50, v => Math.round(v));
  setVal("inp-similarity", s.similarity ? s.similarity * 100 : 75, v => Math.round(v));
  setVal("inp-expressiveness", s.expressiveness ? s.expressiveness * 100 : 50, v => Math.round(v));
  
  setVal("inp-energy", s.energy * 100, v => Math.round(v));
  setVal("inp-warmth", s.warmth * 100, v => Math.round(v));
  setVal("inp-breathiness", s.breathiness * 100, v => Math.round(v));
  setVal("inp-clarity", s.clarity * 100, v => Math.round(v));
  setVal("inp-resonance", s.resonance * 100, v => Math.round(v));
  
  setVal("inp-pause_length", s.pause_length * 100, v => Math.round(v));
  setVal("inp-emphasis", s.emphasis * 100, v => Math.round(v));
  
  if (s.emotion) {
    const radio = document.getElementById(`emo-${s.emotion.toLowerCase()}`);
    if (radio) radio.checked = true;
  }
}

function getCurrentStudioSettings() {
  return {
    speed: Number(document.getElementById("inp-speed").value),
    pitch: Number(document.getElementById("inp-pitch").value),
    stability: Number(document.getElementById("inp-stability").value) / 100,
    similarity: Number(document.getElementById("inp-similarity").value) / 100,
    expressiveness: Number(document.getElementById("inp-expressiveness").value) / 100,
    energy: Number(document.getElementById("inp-energy").value) / 100,
    warmth: Number(document.getElementById("inp-warmth").value) / 100,
    breathiness: Number(document.getElementById("inp-breathiness").value) / 100,
    clarity: Number(document.getElementById("inp-clarity").value) / 100,
    resonance: Number(document.getElementById("inp-resonance").value) / 100,
    pause_length: Number(document.getElementById("inp-pause_length").value) / 100,
    sentence_variation: 0.5, // Not exposed yet
    emphasis: Number(document.getElementById("inp-emphasis").value) / 100,
    emotion: document.querySelector('input[name="emotion"]:checked') ? document.querySelector('input[name="emotion"]:checked').value : "neutral",
    preset: "custom"
  };
}

// Live update of labels
document.querySelectorAll('.vs-control input[type="range"]').forEach(inp => {
  inp.addEventListener('input', (e) => {
    const valEl = document.getElementById(e.target.id.replace("inp-", "val-"));
    if (valEl) {
      if (e.target.id === 'inp-speed') valEl.textContent = Number(e.target.value).toFixed(2) + "×";
      else if (e.target.id === 'inp-pitch') valEl.textContent = Number(e.target.value).toFixed(1);
      else valEl.textContent = e.target.value;
    }
  });
});

// MACRO LOGIC (Voice Character)
function applyMacros() {
  const age = Number(document.getElementById("inp-age").value); // 0 (Young) to 100 (Mature)
  const personality = Number(document.getElementById("inp-personality").value); // 0 (Calm) to 100 (Energetic)
  const authority = Number(document.getElementById("inp-authority").value); // 0 (Casual) to 100 (Commanding)
  
  let pitch = 0;
  let speed = 1.0;
  let warmth = 50;
  let energy = 50;
  let resonance = 50;
  
  // Age logic (Younger = higher pitch, faster. Older = lower pitch, slower, warmer)
  pitch += (50 - age) / 12.0; // +/- 4 semitones roughly
  speed -= (age - 50) / 250.0;
  warmth += (age - 50) / 2.0;
  
  // Personality (Energetic = faster, higher energy)
  speed += (personality - 50) / 200.0;
  energy += (personality - 50);
  
  // Authority (Commanding = slightly lower pitch, higher resonance, more energy)
  pitch -= (authority - 50) / 15.0;
  resonance += (authority - 50);
  energy += (authority - 50) / 2.0;
  
  // Clamp values
  const clamp = (val, min, max) => Math.max(min, Math.min(max, val));
  
  const newSettings = {
    ...getCurrentStudioSettings(),
    pitch: clamp(pitch, -6, 6),
    speed: clamp(speed, 0.75, 1.5),
    warmth: clamp(warmth, 0, 100) / 100,
    energy: clamp(energy, 0, 100) / 100,
    resonance: clamp(resonance, 0, 100) / 100
  };
  
  updateStudioSliders(newSettings);
}

document.getElementById("inp-clarity").addEventListener("input", function() { document.getElementById("val-clarity").textContent = Math.round(this.value); });
document.getElementById("inp-pause_length").addEventListener("input", function() { document.getElementById("val-pause_length").textContent = Math.round(this.value); });
document.getElementById("inp-emphasis").addEventListener("input", function() { document.getElementById("val-emphasis").textContent = Math.round(this.value); });

// Macros Logic
const bindMacro = (id, callback) => {
  const el = document.getElementById(id);
  if (el) {
    el.addEventListener("input", function() {
      document.getElementById(id.replace("inp-", "val-")).textContent = Math.round(this.value);
      callback(Number(this.value));
    });
  }
};

bindMacro("inp-age", (val) => {
  // Age affects pitch (older = deeper) and speed (older = slower)
  const pitch = 2.0 - (val / 100) * 4.0; // 0 -> 2.0, 100 -> -2.0
  const speed = 1.2 - (val / 100) * 0.4; // 0 -> 1.2, 100 -> 0.8
  const pitchEl = document.getElementById("inp-pitch");
  const speedEl = document.getElementById("inp-speed");
  pitchEl.value = pitch;
  document.getElementById("val-pitch").textContent = pitch.toFixed(1);
  speedEl.value = speed;
  document.getElementById("val-speed").textContent = speed.toFixed(2) + "×";
});

bindMacro("inp-personality", (val) => {
  // Personality affects energy and expressiveness
  const energyEl = document.getElementById("inp-energy");
  const exprEl = document.getElementById("inp-expressiveness");
  if(energyEl) { energyEl.value = val; document.getElementById("val-energy").textContent = Math.round(val); }
  if(exprEl) { exprEl.value = val; document.getElementById("val-expressiveness").textContent = Math.round(val); }
});

bindMacro("inp-authority", (val) => {
  // Authority affects resonance and warmth (more authority = less warmth, more resonance)
  const resEl = document.getElementById("inp-resonance");
  const warmthEl = document.getElementById("inp-warmth");
  if(resEl) { resEl.value = val; document.getElementById("val-resonance").textContent = Math.round(val); }
  if(warmthEl) { 
    const warmth = 100 - val;
    warmthEl.value = warmth; 
    document.getElementById("val-warmth").textContent = Math.round(warmth); 
  }
});

// VERSIONS LOGIC
async function loadVoiceVersions() {
  const list = document.getElementById("vsVersionList");
  list.innerHTML = "";
  try {
    const res = await fetch(`${API_BASE}/v1/voices/${activeStudioVoice.id}/versions`);
    const data = await res.json();
    data.versions.forEach(v => {
      const el = document.createElement("div");
      el.className = "version-item";
      el.innerHTML = `
        <div class="version-info">
          <h4>${v.name}</h4>
          <p>Created ${new Date(v.created_at).toLocaleDateString()}</p>
        </div>
        <div class="version-actions">
          <button class="load-ver" title="Load">⬇️</button>
          <button class="del-ver" title="Delete">🗑️</button>
        </div>
      `;
      el.querySelector(".load-ver").onclick = (e) => {
        e.stopPropagation();
        updateStudioSliders(v.settings);
        document.querySelectorAll(".version-item").forEach(i => i.classList.remove("active"));
        el.classList.add("active");
      };
      el.querySelector(".del-ver").onclick = async (e) => {
        e.stopPropagation();
        if (confirm("Delete this version?")) {
          await fetch(`${API_BASE}/v1/voice-versions/${v.id}`, { method: "DELETE" });
          loadVoiceVersions();
        }
      };
      list.appendChild(el);
    });
  } catch (e) {
    console.error(e);
  }
}

document.getElementById("vsSaveVersionBtn").addEventListener("click", async () => {
  const name = document.getElementById("vsNewVersionName").value.trim() || "New Version";
  const settings = getCurrentStudioSettings();
  try {
    await fetch(`${API_BASE}/v1/voices/${activeStudioVoice.id}/versions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, settings })
    });
    document.getElementById("vsNewVersionName").value = "";
    loadVoiceVersions();
  } catch (e) {
    alert("Failed to save version.");
  }
});

// GENERATE & COMPARE LOGIC
document.getElementById("vsGenerateBtn").addEventListener("click", async () => {
  const text = document.getElementById("vsTestText").value.trim();
  if (!text) return alert("Please enter text.");
  
  const btn = document.getElementById("vsGenerateBtn");
  const originalText = btn.textContent;
  btn.textContent = "Generating...";
  btn.disabled = true;
  document.getElementById("vsAudioResult").style.display = "none";
  document.getElementById("vsCompareResult").style.display = "none";
  
  try {
    const settings = getCurrentStudioSettings();
    const result = await generateVoicePreview(activeStudioVoice.id, { text, settings });
    document.getElementById("vsAudioResult").style.display = "block";
    vsPreviewWaveSurfer.load(result.audio_url);
    comparisonSettingsA = settings; // Save as variant A
  } catch (e) {
    alert("Failed: " + e.message);
  } finally {
    btn.textContent = originalText;
    btn.disabled = false;
  }
});

document.getElementById("vsCompareBtn").addEventListener("click", async () => {
  const text = document.getElementById("vsTestText").value.trim();
  if (!text) return alert("Please enter text.");
  if (!comparisonSettingsA) return alert("Please generate a preview first to use as Variant A.");
  
  const btn = document.getElementById("vsCompareBtn");
  const originalText = btn.textContent;
  btn.textContent = "Comparing...";
  btn.disabled = true;
  document.getElementById("vsAudioResult").style.display = "none";
  
  try {
    const settingsB = getCurrentStudioSettings();
    const result = await fetch(`${API_BASE}/v1/voices/${activeStudioVoice.id}/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, settingsA: comparisonSettingsA, settingsB })
    }).then(r => r.json());
    
    document.getElementById("vsCompareResult").style.display = "flex";
    vsCompareWaveA.load(result.audio_url_a);
    vsCompareWaveB.load(result.audio_url_b);
  } catch (e) {
    alert("Failed: " + e.message);
  } finally {
    btn.textContent = originalText;
    btn.disabled = false;
  }
});

// SAVE DEFAULT & RESET
document.getElementById("vsSaveDefaultBtn").addEventListener("click", async () => {
  if (!activeStudioVoice) return;
  const btn = document.getElementById("vsSaveDefaultBtn");
  const original = btn.textContent;
  btn.textContent = "Saving...";
  try {
    await updateVoiceSettings(activeStudioVoice.id, getCurrentStudioSettings());
    btn.textContent = "Saved!";
    setTimeout(() => btn.textContent = original, 2000);
  } catch (e) {
    alert("Error: " + e.message);
    btn.textContent = original;
  }
});

document.getElementById("vsResetBtn").addEventListener("click", async () => {
  if (!activeStudioVoice) return;
  try {
    const data = await resetVoiceSettings(activeStudioVoice.id);
    updateStudioSliders(data.settings);
    
    // Reset Macros UI
    document.getElementById("inp-age").value = 50;
    document.getElementById("inp-personality").value = 50;
    document.getElementById("inp-authority").value = 50;
    document.getElementById("val-age").textContent = "50";
    document.getElementById("val-personality").textContent = "50";
    document.getElementById("val-authority").textContent = "50";
  } catch (e) {
    alert("Error resetting: " + e.message);
  }
});

function closeVoiceStudio() {
  vsOverlay.classList.remove("active");
  vsPanel.classList.remove("active");
  if (vsPreviewWaveSurfer) vsPreviewWaveSurfer.pause();
  if (vsCompareWaveA) vsCompareWaveA.pause();
  if (vsCompareWaveB) vsCompareWaveB.pause();
}

document.getElementById("vsCloseBtn").addEventListener("click", closeVoiceStudio);
vsOverlay.addEventListener("click", closeVoiceStudio);
