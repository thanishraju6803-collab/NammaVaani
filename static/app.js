const $ = (id) => document.getElementById(id);
const LANGS = {
  kn:{name:"ಕನ್ನಡ · Kannada",short:"Kannada",code:"kn-IN"},
  te:{name:"తెలుగు · Telugu",short:"Telugu",code:"te-IN"},
  ta:{name:"தமிழ் · Tamil",short:"Tamil",code:"ta-IN"},
  hi:{name:"हिन्दी · Hindi",short:"Hindi",code:"hi-IN"},
  ml:{name:"മലയാളം · Malayalam",short:"Malayalam",code:"ml-IN"},
  mr:{name:"मराठी · Marathi",short:"Marathi",code:"mr-IN"},
  bn:{name:"বাংলা · Bengali",short:"Bengali",code:"bn-IN"},
  gu:{name:"ગુજરાતી · Gujarati",short:"Gujarati",code:"gu-IN"},
  pa:{name:"ਪੰਜਾਬੀ · Punjabi",short:"Punjabi",code:"pa-IN"},
  en:{name:"English (India)",short:"English",code:"en-IN"},
  auto:{name:"Auto detect",short:"Auto detect",code:"en-IN"}
};
let sessionId = localStorage.getItem("namma_session_id");
if (!sessionId) { sessionId = (crypto.randomUUID ? crypto.randomUUID() : `nv-${Date.now()}-${Math.random()}`); localStorage.setItem("namma_session_id", sessionId); }
let recorder = null;
let audioContext = null;
let inputSource = null;
let processor = null;
let mutedGain = null;
let audioStream = null;
let audioBuffers = [];
let recordingStarted = 0;
let recordingTimer = null;
let lastAnswer = "";
let lastAudioUrl = null;
let currentLanguage = localStorage.getItem("namma_language") || "kn";
let gnaniReady = false;
let autoDetectReady = false;
let translationReady = false;
let savedGpsPoint = null;

function toast(message) {
  const el = $("toast"); el.textContent = message; el.classList.add("show");
  clearTimeout(toast.timer); toast.timer = setTimeout(() => el.classList.remove("show"), 3200);
}
function getLanguage() { return $("languageSelect").value || currentLanguage; }
function updateLanguageLabels() {
  currentLanguage = getLanguage();
  const selected = LANGS[currentLanguage] || LANGS.kn;
  $("languageName").textContent = selected.name;
  localStorage.setItem("namma_language", currentLanguage);
  if ($("settingsLanguage")) $("settingsLanguage").value = currentLanguage;
  const help = $("languageHelp");
  if (help) {
    if (currentLanguage === "auto") {
      help.textContent = autoDetectReady
        ? "Prisma v3.0 will identify the spoken Indian language. You can still choose a language manually."
        : "Automatic detection is unavailable with the current Prisma v2.5 setting. Choose the language you will speak.";
    } else if (["kn", "te", "en"].includes(currentLanguage)) {
      help.textContent = "Choose the main language you will speak. English words can be mixed naturally; review important names, numbers and places.";
    } else if (translationReady) {
      help.textContent = "Multilingual response translation is enabled. NammaVaani will use verified data for answers; please check important names, numbers and instructions.";
    } else {
      help.textContent = "Speech support is available in this language. Full farming conversations need an optional multilingual translation model; until then, replies are in beta.";
    }
  }
}
function setMicState(state, message) {
  const button = $("micButton");
  const stage = document.querySelector(".voice-stage");
  button.classList.toggle("recording", state === "recording");
  stage.classList.toggle("is-recording", state === "recording");
  $("micLabel").textContent = state === "recording" ? "Tap to finish" : state === "working" ? "Listening…" : "Tap to talk";
  $("micStatus").innerHTML = state === "recording" ? "<span class='tiny-mic'>●</span> Recording… tap again to send" : state === "working" ? "◌ Understanding your request…" : (message || "<span class='tiny-mic'>🎙</span> ಮಾತನಾಡಲು ಒತ್ತಿ · Tap to start speaking");
  button.disabled = state === "working";
}

function downsampleBuffer(buffer, inputRate, outputRate) {
  if (outputRate === inputRate) return buffer;
  const ratio = inputRate / outputRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);
  let offsetResult = 0, offsetBuffer = 0;
  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
    let accum = 0, count = 0;
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) { accum += buffer[i]; count++; }
    result[offsetResult] = count ? accum / count : 0;
    offsetResult++; offsetBuffer = nextOffsetBuffer;
  }
  return result;
}
function encodeWav(samples, sampleRate) {
  const bytesPerSample = 2;
  const buffer = new ArrayBuffer(44 + samples.length * bytesPerSample);
  const view = new DataView(buffer);
  const write = (offset, string) => { for (let i=0; i<string.length; i++) view.setUint8(offset+i, string.charCodeAt(i)); };
  write(0, "RIFF"); view.setUint32(4, 36 + samples.length * bytesPerSample, true); write(8, "WAVE");
  write(12, "fmt "); view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * bytesPerSample, true);
  view.setUint16(32, bytesPerSample, true); view.setUint16(34, 16, true); write(36, "data"); view.setUint32(40, samples.length * bytesPerSample, true);
  let offset = 44;
  for (let i=0; i<samples.length; i++, offset += 2) {
    let s = Math.max(-1, Math.min(1, samples[i])); view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buffer], {type: "audio/wav"});
}

async function startRecording() {
  if (!gnaniReady) { toast("Live voice needs a valid GNANI_API_KEY. You can use Type instead for a text test."); return; }
  if (!$("audioConsent").checked) { toast("Please agree before sending your voice to Gnani."); return; }
  if (!navigator.mediaDevices?.getUserMedia) { toast("Microphone access needs HTTPS or localhost and a supported browser."); return; }
  try {
    audioStream = await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true, noiseSuppression:true, autoGainControl:true}});
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    inputSource = audioContext.createMediaStreamSource(audioStream);
    processor = audioContext.createScriptProcessor(4096, 1, 1);
    mutedGain = audioContext.createGain(); mutedGain.gain.value = 0;
    audioBuffers = [];
    processor.onaudioprocess = (event) => audioBuffers.push(new Float32Array(event.inputBuffer.getChannelData(0)));
    inputSource.connect(processor); processor.connect(mutedGain); mutedGain.connect(audioContext.destination);
    recordingStarted = Date.now(); setMicState("recording");
    recordingTimer = setTimeout(stopRecording, 30000);
  } catch (err) {
    toast(err?.message || "Could not access the microphone. Please allow microphone permission.");
    setMicState("idle");
  }
}
async function stopRecording() {
  if (!audioContext || !audioBuffers.length) { setMicState("idle"); return; }
  clearTimeout(recordingTimer);
  const sampleRate = audioContext.sampleRate;
  const total = audioBuffers.reduce((sum, b) => sum + b.length, 0);
  const merged = new Float32Array(total); let offset = 0;
  audioBuffers.forEach(b => { merged.set(b, offset); offset += b.length; });
  const samples = downsampleBuffer(merged, sampleRate, 16000);
  const wav = encodeWav(samples, 16000);
  try { processor.disconnect(); inputSource.disconnect(); mutedGain.disconnect(); } catch (_) {}
  audioStream?.getTracks().forEach(t => t.stop());
  try { await audioContext.close(); } catch (_) {}
  audioContext = null; processor = null; inputSource = null; mutedGain = null; audioStream = null;
  if ((Date.now() - recordingStarted) < 650) { setMicState("idle"); toast("Please speak a little longer."); return; }
  await submitVoice(wav);
}

async function submitVoice(blob) {
  setMicState("working");
  const form = new FormData();
  form.append("file", blob, "farmer-question.wav");
  form.append("language", getLanguage());
  form.append("session_id", sessionId);
  try {
    const response = await fetch("/api/voice", {method:"POST", body:form});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Voice request failed.");
    renderResponse(data);
  } catch (err) {
    toast(err.message || "Could not process this recording.");
  } finally { setMicState("idle"); }
}
async function submitText(text) {
  if (!text.trim()) return;
  const button = $("sendTyped"); button.disabled = true; button.textContent = "Thinking…";
  try {
    const response = await fetch("/api/text", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({text:text.trim(), language:getLanguage(), session_id:sessionId})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Request failed.");
    renderResponse(data);
  } catch (err) { toast(err.message || "Could not process your question."); }
  finally { button.disabled=false; button.textContent="Ask NammaVaani"; }
}
function makeTable(rows, labels) {
  const table = document.createElement("table"); table.className = "detail-table";
  rows.forEach(row => {
    const tr = document.createElement("tr");
    row.forEach(cell => { const td = document.createElement("td"); td.textContent = cell ?? "—"; tr.appendChild(td); });
    table.appendChild(tr);
  });
  return table;
}
function renderResponse(data) {
  lastAnswer = data.answer || "";
  $("resultCard").dataset.replyLanguage = data.reply_language || getLanguage();
  $("resultCard").classList.remove("hidden");
  $("transcriptText").textContent = data.transcript || "Typed question";
  $("answerText").textContent = data.answer || "";
  const detectedName = data.detected_language_name || LANGS[data.detected_language]?.short || "";
  const replyName = data.reply_language_name || "";
  const langNote = $("languageResultNote");
  if (langNote) {
    const detectionMethod = data.detected_language_source === "Prisma language detection" ? " (Prisma)" : data.detected_language_source === "transcript script estimate" ? " (script check)" : "";
    langNote.textContent = detectedName ? `Detected speech: ${detectedName}${detectionMethod}.` : "";
    if (data.language_support === "speech-beta") {
      langNote.textContent += ` Full task conversations are not configured for this language yet.`;
    } else if (data.language_support === "translated") {
      langNote.textContent += " This reply used the configured multilingual translation model. Check important details before confirming an action.";
    }
  }
  const pretty = {weather:"Weather", market:"Market price", crop:"Crop planner", repair:"Farm repair", letter:"Letter draft", crop_health:"Crop health", general:"NammaVaani"};
  $("intentTag").textContent = pretty[data.intent] || "Assistant";
  const details = $("resultDetails"); details.innerHTML = "";
  if (data.weather) {
    const current = data.weather.current || {};
    const daily = (data.weather.daily || []).slice(0,3);
    const box = document.createElement("div"); box.className="data-note";
    box.appendChild(makeTable([["Temperature", `${current.temperature_2m ?? "—"} °C`],["Humidity", `${current.relative_humidity_2m ?? "—"}%`],["Rain now", `${current.precipitation ?? "—"} mm`],["Location", data.weather.location?.name || "—"]]));
    const rows = daily.map(d => [d.date, `${d.temperature_2m_min ?? "—"}° / ${d.temperature_2m_max ?? "—"}°`, `${d.precipitation_sum ?? "—"} mm`]);
    if (rows.length) { const h=document.createElement("div");h.className="field-label";h.textContent="NEXT DAYS";box.appendChild(h);box.appendChild(makeTable(rows)); }
    const cap=document.createElement("p");cap.className="micro-note";cap.textContent=`Source: ${data.weather.attribution || data.weather.source || "Weather service"} · ${data.weather.fetched_at || ""}`;box.appendChild(cap);details.appendChild(box);
  }
  if (data.market_rows?.length) {
    const first = data.market_rows[0];
    details.appendChild(makeTable([["Market",first.market],["Arrival date",first.arrival_date],["Minimum",`₹${first.min_price} / quintal`],["Modal",`₹${first.modal_price} / quintal`],["Maximum",`₹${first.max_price} / quintal`],["Freshness",first.freshness],["Source",first.source || "Agmarknet"],["Retrieved",first.retrieved_at || "—"]]));
    if (first.fallback_note) { const note=document.createElement("p");note.className="micro-note";note.textContent=first.fallback_note;details.appendChild(note); }
  }
  if (data.crop_options?.length) {
    const rows = data.crop_options.slice(0,7).map(x => [x.crop || x.name || "Crop", x.category || x.group || "Local crop option"]);
    details.appendChild(makeTable(rows));
  }
  if (data.letter_text) {
    const pre=document.createElement("pre");pre.className="letter-preview";pre.textContent=data.letter_text;details.appendChild(pre);
    const actions=document.createElement("div");actions.className="result-actions";
    const download=document.createElement("button");download.className="primary-small";download.textContent="⬇ Download letter";download.onclick=()=>downloadText(data.letter_text,data.download_name || "NammaVaani_Letter.txt");
    const copy=document.createElement("button");copy.className="secondary-small";copy.textContent="Copy letter";copy.onclick=()=>navigator.clipboard.writeText(data.letter_text).then(()=>toast("Letter copied."));
    actions.append(download,copy);details.append(actions);
  }
  if (data.ticket_id) {
    const tag=document.createElement("div");tag.className="ticket-result";tag.textContent=`✓ Ticket ${data.ticket_id} created`;details.append(tag);
  }
  if (data.audio_base64) {
    const audio=$("answerAudio");
    if (lastAudioUrl) URL.revokeObjectURL(lastAudioUrl);
    const raw=atob(data.audio_base64);const bytes=new Uint8Array(raw.length);for(let i=0;i<raw.length;i++)bytes[i]=raw.charCodeAt(i);
    lastAudioUrl=URL.createObjectURL(new Blob([bytes],{type:data.audio_mime || "audio/wav"}));audio.src=lastAudioUrl;audio.classList.remove("hidden");
    $("playAnswerButton").textContent="▶ Listen with Gnani Timbre";
  } else {
    $("answerAudio").classList.add("hidden");
    $("playAnswerButton").textContent="▶ Read answer aloud";
  }
  const sttStatus = data.gnani_stt
    ? `Prisma SUCCESS${data.gnani_stt_request_id ? ` · ${data.gnani_stt_request_id}` : ""}${data.gnani_stt_processing_time != null ? ` · ${data.gnani_stt_processing_time}s` : ""}`
    : `Prisma not used (${data.source || "typed input"})`;
  const ttsStatus = data.gnani_tts
    ? `Timbre SUCCESS · ${data.gnani_tts_audio_bytes || 0} bytes`
    : data.tts_error ? `Timbre FAILED · ${data.tts_error}` : "Timbre not called";
  $("sourceLine").textContent=`Gnani usage · ${sttStatus} · ${ttsStatus}`;
  if (data.tts_error) toast(`Timbre API failed: ${data.tts_error}`);
  updateRecent();
  $("resultCard").scrollIntoView({behavior:"smooth",block:"nearest"});
  if (data.audio_base64) { $("answerAudio").play().catch(()=>{}); }
}
function downloadText(text, filename) {
  const blob=new Blob([text],{type:"text/plain;charset=utf-8"});const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download=filename;a.click();URL.revokeObjectURL(url);
}
function playAnswer() {
  const audio=$("answerAudio");
  if (!audio.classList.contains("hidden") && audio.src) { audio.play().catch(()=>toast("Tap the audio play control.")); return; }
  if (!lastAnswer) return;
  if (!window.speechSynthesis) { toast("Speech playback is not available in this browser."); return; }
  const utterance=new SpeechSynthesisUtterance(lastAnswer);utterance.lang=LANGS[$("resultCard").dataset.replyLanguage || getLanguage()]?.code || "en-IN";utterance.rate=.9;window.speechSynthesis.cancel();window.speechSynthesis.speak(utterance);
  $("sourceLine").textContent="Output: Device voice fallback — not Gnani Timbre.";
}
function updateRecent() {
  fetch(`/api/history?session_id=${encodeURIComponent(sessionId)}`).then(r=>r.json()).then(data=>{
    const items=data.items || [];const list=$("recentList");list.innerHTML="";
    if(!items.length){list.innerHTML='<div class="empty-recent"><span>💬</span><p>Your questions and answers will appear here.</p></div>';}
    items.slice(-4).reverse().forEach(item=>list.appendChild(historyItem(item)));
    const page=$("historyPageList");page.innerHTML="";items.slice().reverse().forEach(item=>page.appendChild(historyItem(item)));
  }).catch(()=>{});
}
function historyItem(item) {
  const div=document.createElement("div");div.className="recent-item";
  const symbol=document.createElement("span");symbol.className="recent-symbol";symbol.textContent=({weather:"☀",market:"₹",repair:"🔧",letter:"✉",crop:"🌱"})[item.intent] || "💬";
  const content=document.createElement("div");content.style.flex="1";
  const q=document.createElement("b");q.textContent=item.question;
  const a=document.createElement("p");a.textContent=item.answer;
  const meta=document.createElement("div");meta.className="recent-meta";meta.textContent=item.intent || "conversation";
  content.append(q,a,meta);div.append(symbol,content);return div;
}
function navigate(viewId) {
  document.querySelectorAll(".view").forEach(v=>v.classList.toggle("active",v.id===viewId));
  document.querySelectorAll(".nav-item").forEach(n=>n.classList.toggle("active",n.dataset.view===viewId));
  if(viewId==="activityView")loadTickets();
  if(viewId==="farmView")loadProfile();
  window.scrollTo({top:0,behavior:"smooth"});
}
async function loadHealth() {
  try {
    const r=await fetch("/api/health");const d=await r.json();
    gnaniReady = !!d.gnani_configured;
    autoDetectReady = !!d.auto_detect_enabled;
    translationReady = !!d.translation_enabled;
    const storedLanguage = localStorage.getItem("namma_language");
    if (storedLanguage === "auto" && autoDetectReady) $("languageSelect").value = "auto";
    [$("languageSelect").querySelector('option[value="auto"]'), $("settingsLanguage").querySelector('option[value="auto"]')].forEach(option => {
      if (option) option.disabled = !autoDetectReady;
    });
    if (currentLanguage === "auto" && !autoDetectReady) {
      $("languageSelect").value = "kn";
      currentLanguage = "kn";
    }
    updateLanguageLabels();
    const el=$("gnaniStatus");
    const modelName = d.stt_model || "prisma-v2.5";
    el.textContent=gnaniReady?`Key found (${d.gnani_key_source || "environment"}) · ${modelName} · not yet API-verified${translationReady ? " · multilingual bridge on" : ""}`:"API key not configured";
    el.style.color=gnaniReady?"#9a6a20":"#a45b45";
    if (!gnaniReady) $("micStatus").textContent="Live voice is not configured yet · Type instead to test";
    const mandiStatus=$("mandiSourceStatus");
    if (mandiStatus) mandiStatus.textContent=d.mandi_api_configured ? "Mandi source: government API first · CSV backup available." : "Mandi source: add DATA_GOV_IN_API_KEY for automatic lookup, or upload the official CSV.";
  } catch(_){$("gnaniStatus").textContent="Status unavailable";}
}
async function loadProfile() {
  try {
    const r=await fetch("/api/profile");const p=await r.json();
    const displayLocation = p.village || p.taluk || p.hobli || p.district || p.location || "";
    const hasSpecificLocation = !!(p.village || p.taluk || p.hobli || (p.location && !["Bengaluru, Karnataka, India", "Bengaluru Urban"].includes(p.location)) || (p.gps_consent && p.latitude != null));
    $("headerLocation").textContent=hasSpecificLocation ? displayLocation : "Set your village";
    $("farmState").value=p.state || "Karnataka";$("farmDistrict").value=p.district || "";
    $("farmTaluk").value=p.taluk || "";$("farmHobli").value=p.hobli || "";$("farmLocation").value=p.village || "";
    $("farmLand").value=p.land_acres ?? "";$("farmSoil").value=p.soil_type || "Unknown";$("farmWater").value=p.irrigation || "Unknown";$("farmCrop").value=p.current_crop || "";
    savedGpsPoint = (p.gps_consent && p.latitude != null && p.longitude != null) ? {latitude:p.latitude,longitude:p.longitude} : null;
    $("farmGpsConsent").checked = !!p.gps_consent;$("getFarmGps").disabled = !p.gps_consent;
    if (savedGpsPoint) { $("farmLatitude").value=savedGpsPoint.latitude;$("farmLongitude").value=savedGpsPoint.longitude;$("gpsFeedback").textContent="GPS saved with your consent. Weather can use this farm point."; }
    else { $("farmLatitude").value="";$("farmLongitude").value="";$("gpsFeedback").textContent="GPS is off. Your location will not be accessed unless you opt in and press the button."; }
    const legacyLanguageCodes = {"Kannada":"kn", "Telugu":"te", "English":"en", "English (India)":"en", "Tamil":"ta", "Hindi":"hi", "Malayalam":"ml", "Marathi":"mr", "Bengali":"bn", "Gujarati":"gu", "Punjabi":"pa"};
    const savedLanguage = legacyLanguageCodes[p.preferred_language] || p.preferred_language;
    if(savedLanguage && LANGS[savedLanguage] && (savedLanguage !== "auto" || autoDetectReady)){$("languageSelect").value=savedLanguage;updateLanguageLabels();}
  } catch(_){ }
}
async function saveProfile(event) {
  event.preventDefault();
  const gpsConsent=$("farmGpsConsent").checked;
  if (gpsConsent && !savedGpsPoint) { $("farmFeedback").textContent="Please press 'Use my current location' or turn GPS consent off."; return; }
  const data={state:$("farmState").value.trim(),district:$("farmDistrict").value.trim(),taluk:$("farmTaluk").value.trim(),hobli:$("farmHobli").value.trim(),village:$("farmLocation").value.trim(),land_acres:$("farmLand").value?Number($("farmLand").value):null,soil_type:$("farmSoil").value,irrigation:$("farmWater").value,current_crop:$("farmCrop").value.trim(),preferred_language:getLanguage(),gps_consent:gpsConsent,latitude:gpsConsent?savedGpsPoint.latitude:null,longitude:gpsConsent?savedGpsPoint.longitude:null};
  try {const r=await fetch("/api/profile",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});const d=await r.json();if(!r.ok)throw new Error(d.detail||"Could not save profile.");$("farmFeedback").textContent="Your farm details have been saved.";$("headerLocation").textContent=data.village || data.taluk || data.district || "Set your village";toast("My Farm details saved.");}
  catch(err){$("farmFeedback").textContent=err.message;}
}
async function uploadMandi() {
  const file=$("mandiFile").files?.[0];if(!file){toast("Choose an Agmarknet CSV first.");return;}
  const form=new FormData();form.append("file",file);
  $("uploadFeedback").textContent="Uploading…";
  try {const r=await fetch("/api/mandi-upload",{method:"POST",body:form});const d=await r.json();if(!r.ok)throw new Error(d.detail||"Upload failed.");$("uploadFeedback").textContent=d.message;toast("Mandi data saved.");}
  catch(err){$("uploadFeedback").textContent=err.message;}
}
async function testTimbre() {
  const button = $("testTimbreButton");
  const feedback = $("testTimbreFeedback");
  button.disabled = true; button.textContent = "Testing…";
  feedback.textContent = "Sending a short test phrase to Gnani Timbre v2.5…";
  try {
    const form = new FormData();
    form.append("language", getLanguage() === "auto" ? "kn" : getLanguage());
    const response = await fetch("/api/gnani/test-tts", {method:"POST", body:form});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Timbre test failed.");
    if (lastAudioUrl) URL.revokeObjectURL(lastAudioUrl);
    const raw = atob(data.audio_base64);
    const bytes = new Uint8Array(raw.length);
    for (let i=0; i<raw.length; i++) bytes[i] = raw.charCodeAt(i);
    lastAudioUrl = URL.createObjectURL(new Blob([bytes], {type:data.audio_mime || "audio/wav"}));
    const audio = $("answerAudio"); audio.src = lastAudioUrl; audio.classList.remove("hidden");
    $("playAnswerButton").textContent = "▶ Listen with Gnani Timbre";
    feedback.textContent = `SUCCESS · ${data.model} · HTTP ${data.http_status} · ${data.audio_bytes} audio bytes · ${data.voice} · This was a real Gnani request.`;
    audio.play().catch(()=>{});
    toast("Gnani Timbre test succeeded. Check your Gnani usage dashboard.");
  } catch (err) {
    feedback.textContent = `FAILED · ${err.message}`;
    toast(err.message || "Gnani Timbre test failed.");
  } finally {
    button.disabled = false; button.textContent = "Test Timbre";
  }
}

async function loadTickets() {
  try {const r=await fetch("/api/tickets");const d=await r.json();const box=$("ticketList");box.innerHTML="";if(!d.items?.length){box.innerHTML='<div class="empty-recent">No repair requests yet.</div>';return;}
    d.items.forEach(t=>{const item=document.createElement("div");item.className="recent-item";const sym=document.createElement("span");sym.className="recent-symbol";sym.textContent="🔧";const c=document.createElement("div");c.style.flex="1";const b=document.createElement("b");b.textContent=`${t.ticket_id} · ${t.equipment}`;const p=document.createElement("p");p.textContent=`${t.problem} · ${t.village} · ${t.status}`;c.append(b,p);item.append(sym,c);box.append(item);});
  }catch(_){ }
}

$("micButton").addEventListener("click",()=>{if(audioContext){stopRecording();}else{startRecording();}});
$("languageSelect").addEventListener("change",updateLanguageLabels);
$("settingsLanguage").addEventListener("change",e=>{$("languageSelect").value=e.target.value;updateLanguageLabels();});
$("toggleType").addEventListener("click",()=>$("typedBox").classList.toggle("hidden"));
$("sendTyped").addEventListener("click",()=>{const text=$("typedQuestion").value;submitText(text);});
$("playAnswerButton").addEventListener("click",playAnswer);
$("copyAnswerButton").addEventListener("click",()=>{if(lastAnswer)navigator.clipboard.writeText(lastAnswer).then(()=>toast("Answer copied."));});
$("farmForm").addEventListener("submit",saveProfile);
$("farmGpsConsent").addEventListener("change",e=>{
  const allowed=e.target.checked;$("getFarmGps").disabled=!allowed;
  if(!allowed){savedGpsPoint=null;$("farmLatitude").value="";$("farmLongitude").value="";$("gpsFeedback").textContent="GPS is off. Coordinates will not be saved.";}
  else $("gpsFeedback").textContent="Consent enabled. Press the button to ask your browser for location permission.";
});
$("getFarmGps").addEventListener("click",()=>{
  if(!$("farmGpsConsent").checked){toast("Please opt in first.");return;}
  if(!navigator.geolocation){$("gpsFeedback").textContent="This browser does not support GPS location.";return;}
  $("gpsFeedback").textContent="Waiting for browser location permission…";
  navigator.geolocation.getCurrentPosition(position=>{
    savedGpsPoint={latitude:Number(position.coords.latitude.toFixed(6)),longitude:Number(position.coords.longitude.toFixed(6))};
    $("farmLatitude").value=savedGpsPoint.latitude;$("farmLongitude").value=savedGpsPoint.longitude;
    $("gpsFeedback").textContent=`Location captured: ${savedGpsPoint.latitude}, ${savedGpsPoint.longitude}. Save My Farm to keep it.`;
  },error=>{
    const messages={1:"Location permission was denied. You can continue without GPS.",2:"Your location could not be found. Try again or continue without GPS.",3:"Location request timed out. Try again or continue without GPS."};
    $("gpsFeedback").textContent=messages[error.code] || "GPS is unavailable. You can continue without it.";
  },{enableHighAccuracy:false,timeout:10000,maximumAge:60000});
});
$("uploadMandi").addEventListener("click",uploadMandi);
$("testTimbreButton").addEventListener("click",testTimbre);
$("profileShortcut").addEventListener("click",()=>navigate("farmView"));
$("viewHistory").addEventListener("click",()=>navigate("activityView"));
document.querySelectorAll(".nav-item").forEach(button=>button.addEventListener("click",()=>navigate(button.dataset.view)));
document.querySelectorAll(".question-chip").forEach(button=>button.addEventListener("click",()=>{const prompt=button.dataset.prompt;$("languageSelect").value=button.dataset.lang || getLanguage();updateLanguageLabels();$("typedBox").classList.remove("hidden");$("typedQuestion").value=prompt;$("typedQuestion").focus();toast("Example added. You can edit it and ask.");}));
$("menuButton").addEventListener("click",()=>navigate("settingsView"));
const savedUiLanguage = localStorage.getItem("namma_language");
if (savedUiLanguage && LANGS[savedUiLanguage] && savedUiLanguage !== "auto") $("languageSelect").value = savedUiLanguage;
updateLanguageLabels();loadHealth();loadProfile();updateRecent();
