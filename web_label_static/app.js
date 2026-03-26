const state = {
  ready: false,
  frameCount: 0,
  frameIndex: 0,
  width: 1280,
  height: 720,
  labelHz: 10,
  labelStep: 1,
  annotation: { ball: 0, x: -1, y: -1, labeled: false, reviewed: false },
  dirty: false,
  image: null,
  saveTimer: null,
  toastTimer: null,
  requestToken: 0,
};

const els = {
  videoName: document.getElementById('videoName'),
  csvPath: document.getElementById('csvPath'),
  progressText: document.getElementById('progressText'),
  percentText: document.getElementById('percentText'),
  dirtyText: document.getElementById('dirtyText'),
  labelRateText: document.getElementById('labelRateText'),
  labelStepText: document.getElementById('labelStepText'),
  progressFill: document.getElementById('progressFill'),
  frameIndicator: document.getElementById('frameIndicator'),
  frameStatus: document.getElementById('frameStatus'),
  ballValue: document.getElementById('ballValue'),
  xValue: document.getElementById('xValue'),
  yValue: document.getElementById('yValue'),
  frameSlider: document.getElementById('frameSlider'),
  frameInput: document.getElementById('frameInput'),
  frameCanvas: document.getElementById('frameCanvas'),
  loadingMask: document.getElementById('loadingMask'),
  toast: document.getElementById('toast'),
  pickVideoBtn: document.getElementById('pickVideoBtn'),
  replaceVideoBtn: document.getElementById('replaceVideoBtn'),
  saveBtn: document.getElementById('saveBtn'),
  clearBtn: document.getElementById('clearBtn'),
  nextUnlabeledBtn: document.getElementById('nextUnlabeledBtn'),
  firstBtn: document.getElementById('firstBtn'),
  prevFastBtn: document.getElementById('prevFastBtn'),
  prevBtn: document.getElementById('prevBtn'),
  nextBtn: document.getElementById('nextBtn'),
  nextFastBtn: document.getElementById('nextFastBtn'),
  lastBtn: document.getElementById('lastBtn'),
  jumpBtn: document.getElementById('jumpBtn'),
  emptyState: document.getElementById('emptyState'),
  workspace: document.getElementById('workspace'),
};

const ctx = els.frameCanvas.getContext('2d');

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || '请求失败');
  }
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json();
  }
  return response.blob();
}

function showToast(message, isError = false) {
  els.toast.textContent = message;
  els.toast.classList.toggle('error', isError);
  els.toast.classList.add('show');
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => els.toast.classList.remove('show'), 2200);
}

function setLoading(loading) {
  els.loadingMask.classList.toggle('visible', loading);
}

function clampFrame(index) {
  if (state.frameCount <= 0) return 0;
  return Math.max(0, Math.min(index, state.frameCount - 1));
}

function stepSize() {
  return Math.max(1, Number(state.labelStep) || 1);
}

function setReadyMode(ready) {
  state.ready = ready;
  els.emptyState.classList.toggle('hidden', ready);
  els.workspace.classList.toggle('hidden', !ready);
  els.replaceVideoBtn.disabled = !ready;
  els.saveBtn.disabled = !ready;
}

function renderCanvas() {
  ctx.clearRect(0, 0, els.frameCanvas.width, els.frameCanvas.height);
  if (!state.image) return;

  ctx.drawImage(state.image, 0, 0, els.frameCanvas.width, els.frameCanvas.height);
  if (!state.annotation.labeled) return;

  const x = state.annotation.x * els.frameCanvas.width;
  const y = state.annotation.y * els.frameCanvas.height;
  ctx.beginPath();
  ctx.arc(x, y, 8, 0, Math.PI * 2);
  ctx.fillStyle = '#ff5a4f';
  ctx.fill();
  ctx.lineWidth = 3;
  ctx.strokeStyle = '#ffffff';
  ctx.stroke();
}

function updateAnnotationPanel() {
  const labeled = state.annotation.labeled;
  const reviewed = state.annotation.reviewed;
  els.frameIndicator.textContent = `Frame ${state.frameIndex} / ${Math.max(state.frameCount - 1, 0)}`;
  els.frameStatus.textContent = labeled ? '已标注有球' : (reviewed ? '已检查无球' : '未检查');
  els.frameStatus.classList.toggle('labeled', labeled);
  els.frameStatus.classList.toggle('reviewed', !labeled && reviewed);
  els.ballValue.textContent = String(state.annotation.ball);
  els.xValue.textContent = Number(state.annotation.x).toFixed(3);
  els.yValue.textContent = Number(state.annotation.y).toFixed(3);
  els.frameSlider.value = String(state.frameIndex);
  els.frameInput.value = String(state.frameIndex);
}

function updateProgress(progress) {
  els.progressText.textContent = `${progress.labeled} / ${progress.total}`;
  els.percentText.textContent = `${progress.percent.toFixed(2)}% · 有球 ${progress.positive}`;
  els.progressFill.style.width = `${progress.percent}%`;
}

function updateDirty(dirty) {
  state.dirty = dirty;
  els.dirtyText.textContent = dirty ? '未保存' : '已保存';
  els.dirtyText.classList.toggle('danger-text', dirty);
}

function applyState(payload) {
  setReadyMode(Boolean(payload.ready));
  state.frameCount = payload.frame_count;
  state.width = payload.width;
  state.height = payload.height;
  state.labelHz = Number(payload.label_hz) || 10;
  state.labelStep = Number(payload.label_step) || 1;

  els.videoName.textContent = payload.video_name || '未选择';
  els.csvPath.textContent = payload.csv_path || '将自动生成同名 csv';
  els.labelRateText.textContent = `${state.labelHz.toFixed(2)} Hz`;
  els.labelStepText.textContent = `每 ${stepSize()} 帧标注一次`;
  els.frameSlider.max = String(Math.max(payload.frame_count - 1, 0));
  els.frameInput.max = String(Math.max(payload.frame_count - 1, 0));
  els.frameCanvas.width = payload.width;
  els.frameCanvas.height = payload.height;
  updateProgress(payload.progress);
  updateDirty(payload.dirty);
}

async function loadState() {
  const payload = await api('/api/state');
  applyState(payload);
  return payload;
}

async function loadFrame(frameIndex) {
  state.frameIndex = clampFrame(frameIndex);
  const requestToken = ++state.requestToken;
  setLoading(true);
  try {
    const [annotation, imageBlob] = await Promise.all([
      api(`/api/annotation?index=${state.frameIndex}`),
      api(`/api/frame?index=${state.frameIndex}`),
    ]);
    state.annotation = annotation;
    const image = new Image();
    const objectUrl = URL.createObjectURL(imageBlob);
    await new Promise((resolve, reject) => {
      image.onload = resolve;
      image.onerror = reject;
      image.src = objectUrl;
    });
    if (requestToken !== state.requestToken) {
      URL.revokeObjectURL(objectUrl);
      return;
    }
    state.image = image;
    renderCanvas();
    updateAnnotationPanel();
    URL.revokeObjectURL(objectUrl);
  } finally {
    if (requestToken === state.requestToken) {
      setLoading(false);
    }
  }
}

function scheduleAutosave() {
  clearTimeout(state.saveTimer);
  state.saveTimer = setTimeout(() => {
    saveCurrent(false).catch((error) => showToast(error.message, true));
  }, 1200);
}

async function saveCurrent(showMessage = true) {
  const payload = await api('/api/save', { method: 'POST', body: '{}' });
  updateProgress(payload.progress);
  updateDirty(payload.dirty);
  if (showMessage) {
    showToast(`已保存到 ${payload.csv_path}`);
  }
}

async function goNextAfterMarking() {
  const nextFrame = clampFrame(state.frameIndex + stepSize());
  if (nextFrame !== state.frameIndex) {
    await loadFrame(nextFrame);
  }
}

async function annotateCurrent(normalizedX, normalizedY) {
  const payload = await api('/api/annotate', {
    method: 'POST',
    body: JSON.stringify({ frame: state.frameIndex, x: normalizedX, y: normalizedY }),
  });
  state.annotation = payload.annotation;
  updateProgress(payload.progress);
  updateDirty(payload.dirty);
  renderCanvas();
  updateAnnotationPanel();
  scheduleAutosave();
  await goNextAfterMarking();
}

async function clearCurrent(showMessage = true) {
  const payload = await api('/api/clear', {
    method: 'POST',
    body: JSON.stringify({ frame: state.frameIndex }),
  });
  state.annotation = payload.annotation;
  updateProgress(payload.progress);
  updateDirty(payload.dirty);
  renderCanvas();
  updateAnnotationPanel();
  scheduleAutosave();
  if (showMessage) {
    showToast('当前帧已标记为无球');
  }
  await goNextAfterMarking();
}

async function jumpToNextUnlabeled() {
  const payload = await api(`/api/next_unlabeled?from=${state.frameIndex}&direction=1`);
  if (!payload.found) {
    showToast('后续采样帧都已经检查完成');
    return;
  }
  await loadFrame(payload.frame);
}

async function chooseVideo() {
  setLoading(true);
  try {
    const payload = await api('/api/select_video', { method: 'POST', body: '{}' });
    applyState({ ...payload, ready: true });
    state.frameIndex = 0;
    await loadFrame(0);
    showToast('视频已加载，可以开始标注了');
  } finally {
    setLoading(false);
  }
}

function onCanvasClick(event) {
  if (!state.ready) return;
  const rect = els.frameCanvas.getBoundingClientRect();
  const x = (event.clientX - rect.left) / rect.width;
  const y = (event.clientY - rect.top) / rect.height;
  annotateCurrent(x, y).catch((error) => showToast(error.message, true));
}

function bindActions() {
  els.pickVideoBtn.addEventListener('click', () => chooseVideo().catch((error) => showToast(error.message, true)));
  els.replaceVideoBtn.addEventListener('click', () => chooseVideo().catch((error) => showToast(error.message, true)));
  els.saveBtn.addEventListener('click', () => saveCurrent(true).catch((error) => showToast(error.message, true)));

  els.frameCanvas.addEventListener('click', onCanvasClick);
  els.frameCanvas.addEventListener('contextmenu', (event) => {
    event.preventDefault();
    if (!state.ready) return;
    clearCurrent(false).catch((error) => showToast(error.message, true));
  });

  els.clearBtn.addEventListener('click', () => clearCurrent(true).catch((error) => showToast(error.message, true)));
  els.nextUnlabeledBtn.addEventListener('click', () => jumpToNextUnlabeled().catch((error) => showToast(error.message, true)));
  els.firstBtn.addEventListener('click', () => loadFrame(0).catch((error) => showToast(error.message, true)));
  els.prevBtn.addEventListener('click', () => loadFrame(state.frameIndex - stepSize()).catch((error) => showToast(error.message, true)));
  els.nextBtn.addEventListener('click', () => loadFrame(state.frameIndex + stepSize()).catch((error) => showToast(error.message, true)));
  els.prevFastBtn.addEventListener('click', () => loadFrame(state.frameIndex - (36 * stepSize())).catch((error) => showToast(error.message, true)));
  els.nextFastBtn.addEventListener('click', () => loadFrame(state.frameIndex + (36 * stepSize())).catch((error) => showToast(error.message, true)));
  els.lastBtn.addEventListener('click', () => loadFrame(state.frameCount - 1).catch((error) => showToast(error.message, true)));

  els.frameSlider.addEventListener('input', () => {
    els.frameInput.value = els.frameSlider.value;
  });
  els.frameSlider.addEventListener('change', () => {
    loadFrame(Number(els.frameSlider.value)).catch((error) => showToast(error.message, true));
  });
  els.jumpBtn.addEventListener('click', () => {
    loadFrame(Number(els.frameInput.value)).catch((error) => showToast(error.message, true));
  });
  els.frameInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      loadFrame(Number(els.frameInput.value)).catch((error) => showToast(error.message, true));
    }
  });

  window.addEventListener('keydown', (event) => {
    if (!state.ready) return;
    const activeTag = document.activeElement?.tagName;
    if (activeTag === 'INPUT' || activeTag === 'TEXTAREA') return;

    if (event.key === '[' || (event.metaKey && event.key === 'ArrowLeft')) {
      event.preventDefault();
      loadFrame(0).catch((error) => showToast(error.message, true));
    } else if (event.key === ']' || (event.metaKey && event.key === 'ArrowRight')) {
      event.preventDefault();
      loadFrame(state.frameCount - 1).catch((error) => showToast(error.message, true));
    } else if (event.key === 'ArrowRight') {
      event.preventDefault();
      loadFrame(state.frameIndex + (event.shiftKey ? 36 * stepSize() : stepSize())).catch((error) => showToast(error.message, true));
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault();
      loadFrame(state.frameIndex - (event.shiftKey ? 36 * stepSize() : stepSize())).catch((error) => showToast(error.message, true));
    } else if (event.key.toLowerCase() === 's') {
      event.preventDefault();
      saveCurrent(true).catch((error) => showToast(error.message, true));
    } else if (event.key.toLowerCase() === 'c') {
      event.preventDefault();
      clearCurrent(true).catch((error) => showToast(error.message, true));
    } else if (event.key.toLowerCase() === 'u') {
      event.preventDefault();
      jumpToNextUnlabeled().catch((error) => showToast(error.message, true));
    }
  });

  window.addEventListener('beforeunload', (event) => {
    if (!state.dirty) return;
    event.preventDefault();
    event.returnValue = '';
  });
}

async function init() {
  try {
    bindActions();
    const payload = await loadState();
    if (payload.ready) {
      await loadFrame(0);
    }
  } catch (error) {
    showToast(error.message, true);
  }
}

init();
