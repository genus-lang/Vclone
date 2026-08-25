const API_BASE = "";

async function getVoices() {
  const response = await fetch(`${API_BASE}/v1/voices`);

  if (!response.ok) {
    throw new Error("Failed to load voices");
  }

  return response.json();
}

async function generateSpeech(payload) {
  const response = await fetch(
    `${API_BASE}/v1/audio/speech`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Speech generation failed");
  }

  return response.json();
}

async function getHistory() {
  const response = await fetch(`${API_BASE}/v1/history`);
  if (!response.ok) {
    throw new Error("Failed to load history");
  }
  return response.json();
}

async function deleteAudio(id) {
  const response = await fetch(`${API_BASE}/v1/audio/${id}`, {
    method: "DELETE"
  });
  if (!response.ok) {
    throw new Error("Failed to delete audio");
  }
  return response.json();
}

async function addPronunciation(original, sayAs, language) {
  const response = await fetch(`${API_BASE}/v1/pronunciations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ original: original, say_as: sayAs, language: language || "all" })
  });
  if (!response.ok) {
    throw new Error("Failed to add pronunciation");
  }
  return response.json();
}

async function getPronunciations() {
  const response = await fetch(`${API_BASE}/v1/pronunciations`);
  if (!response.ok) throw new Error("Failed to get pronunciations");
  return response.json();
}

async function deletePronunciation(id) {
  const response = await fetch(`${API_BASE}/v1/pronunciations/${id}`, {
    method: "DELETE"
  });
  if (!response.ok) throw new Error("Failed to delete pronunciation");
  return response.json();
}

async function deleteVoice(id) {
  const response = await fetch(`${API_BASE}/v1/voices/${id}`, {
    method: "DELETE"
  });
  if (!response.ok) {
    throw new Error("Failed to delete voice");
  }
  return response.json();
}

async function getVoiceSettings(id) {
  const response = await fetch(`${API_BASE}/v1/voices/${id}/settings`);
  if (!response.ok) throw new Error("Failed to get settings");
  return response.json();
}

async function updateVoiceSettings(id, settings) {
  const response = await fetch(`${API_BASE}/v1/voices/${id}/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings)
  });
  if (!response.ok) throw new Error("Failed to update settings");
  return response.json();
}

async function resetVoiceSettings(id) {
  const response = await fetch(`${API_BASE}/v1/voices/${id}/settings/reset`, {
    method: "POST"
  });
  if (!response.ok) throw new Error("Failed to reset settings");
  return response.json();
}

async function generateVoicePreview(id, payload) {
  const response = await fetch(`${API_BASE}/v1/voices/${id}/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error("Failed to generate preview");
  return response.json();
}
