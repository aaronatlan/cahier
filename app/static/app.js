(() => {
  "use strict";

  const state = {
    screen: "library",
    subjects: [],
    courses: [],
    search: "",
    selectedSubjectCode: "",
    currentId: null,
    activeTab: "transcription",
    recState: "idle", // idle | recording | transcribing
    recordStartedAt: null,
    timerInterval: null,
    pollInterval: null,
  };

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  async function api(path, opts) {
    const res = await fetch(path, opts);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Erreur ${res.status}`);
    }
    const contentType = res.headers.get("content-type") || "";
    return contentType.includes("application/json") ? res.json() : null;
  }

  function formatDate(iso) {
    const d = new Date(iso);
    return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short" }) +
      " " + d.getFullYear();
  }

  function formatDuration(sec) {
    const s = Math.round(sec || 0);
    if (s < 60) return `${s} s`;
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (h) return `${h} h ${String(m).padStart(2, "0")}`;
    return `${m} min`;
  }

  function formatTimer(sec) {
    const m = Math.floor(sec / 60).toString().padStart(2, "0");
    const s = Math.floor(sec % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  }

  // --- Barre de titre custom (fenêtre frameless pywebview) ---------------

  function callWindowAPI(method) {
    if (window.pywebview && window.pywebview.api && window.pywebview.api[method]) {
      window.pywebview.api[method]();
    } else {
      // Le pont pywebview.api n'est pas encore prêt (ou a échoué à s'injecter) :
      // on retente une fois que pywebview signale qu'il est prêt.
      window.addEventListener("pywebviewready", () => callWindowAPI(method), { once: true });
    }
  }

  function closeWindow() {
    callWindowAPI("close");
  }

  function updateTitlebar() {
    let text = "Cahier";
    if (state.screen === "recording") text = "Nouvel enregistrement";
    if (state.screen === "detail") {
      const course = state.courses.find((c) => c.id === state.currentId);
      if (course) text = course.matiere_titre;
    }
    $("#titlebar-text").textContent = text;
  }

  // --- Navigation ---------------------------------------------------

  function showScreen(screen) {
    state.screen = screen;
    $("#view-library").hidden = screen !== "library";
    $("#view-recording").hidden = screen !== "recording";
    $("#view-detail").hidden = screen !== "detail";
    updateTitlebar();
  }

  function goLibrary() {
    clearInterval(state.timerInterval);
    clearInterval(state.pollInterval);
    state.recState = "idle";
    showScreen("library");
    loadCourses();
  }

  function goRecording() {
    showScreen("recording");
    resetRecordUI();
  }

  // --- Bibliothèque ---------------------------------------------------

  async function loadSubjects() {
    state.subjects = await api("/api/subjects");
    if (!state.selectedSubjectCode && state.subjects.length) {
      state.selectedSubjectCode = state.subjects[0].code;
    }
    const select = $("#subject-select");
    select.innerHTML = "";
    for (const subj of state.subjects) {
      const opt = document.createElement("option");
      opt.value = subj.code;
      opt.textContent = `${subj.titre} (${subj.code})`;
      select.appendChild(opt);
    }
    select.value = state.selectedSubjectCode;
  }

  async function loadCourses() {
    state.courses = await api("/api/courses");
    renderLibrary();
  }

  function groupedSubjects() {
    const q = state.search.trim().toLowerCase();
    const bySubjectCode = new Map();
    for (const course of state.courses) {
      const code = course.matiere || "";
      if (!bySubjectCode.has(code)) {
        bySubjectCode.set(code, { code, titre: course.matiere_titre, sessions: [] });
      }
      bySubjectCode.get(code).sessions.push(course);
    }

    const orderedCodes = [...state.subjects.map((s) => s.code), ""];
    const groups = [];
    for (const code of orderedCodes) {
      const group = bySubjectCode.get(code);
      if (!group) continue;
      let sessions = group.sessions;
      if (q) {
        const subjectMatches = (group.titre + " " + group.code).toLowerCase().includes(q);
        if (!subjectMatches) {
          sessions = sessions.filter((s) =>
            (s.titre + " " + formatDate(s.date)).toLowerCase().includes(q)
          );
        }
      }
      if (sessions.length) groups.push({ ...group, sessions });
    }
    return groups;
  }

  function renderLibrary() {
    const groups = groupedSubjects();
    const container = $("#subject-groups");
    container.innerHTML = "";

    for (const group of groups) {
      const groupEl = document.createElement("div");
      groupEl.className = "subject-group";

      const header = document.createElement("div");
      header.className = "subject-header";
      header.innerHTML = `<h2>${escapeHtml(group.titre)}</h2><span class="subject-meta">${escapeHtml(group.code)} · ${group.sessions.length} cours</span>`;
      groupEl.appendChild(header);

      const list = document.createElement("div");
      list.className = "session-list";

      for (const session of group.sessions) {
        const row = document.createElement("div");
        row.className = "session-row";
        row.addEventListener("click", () => selectCourse(session.id));

        const info = document.createElement("div");
        info.className = "session-info";
        const label = document.createElement("div");
        label.className = "session-label";
        label.textContent = session.titre;
        const meta = document.createElement("div");
        meta.className = "session-meta";
        meta.textContent = `${formatDate(session.date)} · ${formatDuration(session.duree_sec)}`;
        info.appendChild(label);
        info.appendChild(meta);

        const badges = document.createElement("div");
        badges.className = "session-badges";
        if (session.statut === "transcribing" || session.statut === "recording") {
          badges.appendChild(makeBadge(
            session.statut === "recording" ? "En cours" : "Transcription…", false
          ));
        }
        if (session.a_des_slides) badges.appendChild(makeBadge("Slides", false));
        if (session.statut_fiche === "genere") badges.appendChild(makeBadge("Fiche prête", true));

        row.appendChild(info);
        row.appendChild(badges);
        list.appendChild(row);
      }

      groupEl.appendChild(list);
      container.appendChild(groupEl);
    }

    const empty = $("#empty-library");
    if (groups.length === 0) {
      empty.hidden = false;
      empty.textContent = state.search
        ? `Aucun résultat pour « ${state.search} ».`
        : "Aucun cours pour l'instant. Clique « + Nouveau cours » pour commencer.";
    } else {
      empty.hidden = true;
    }
  }

  function makeBadge(text, accent) {
    const span = document.createElement("span");
    span.className = "badge" + (accent ? " badge-accent" : "");
    span.textContent = text;
    return span;
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // --- Enregistrement ---------------------------------------------------

  function resetRecordUI() {
    state.recState = "idle";
    $("#record-btn").className = "record-btn";
    $("#record-icon").className = "record-icon";
    $("#record-timer").textContent = "00:00";
    $("#record-status").textContent = "Prêt";
    $("#subject-select").disabled = false;
  }

  function tick() {
    const elapsed = (Date.now() - state.recordStartedAt) / 1000;
    $("#record-timer").textContent = formatTimer(elapsed);
  }

  async function startRecording() {
    try {
      await api("/api/record/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ matiere: state.selectedSubjectCode }),
      });
    } catch (err) {
      $("#record-status").textContent = err.message;
      return;
    }
    state.recState = "recording";
    state.recordStartedAt = Date.now();
    $("#record-btn").className = "record-btn is-recording";
    $("#record-icon").className = "record-icon is-recording";
    $("#record-status").textContent = "Enregistrement…";
    $("#subject-select").disabled = true;
    tick();
    state.timerInterval = setInterval(tick, 500);
  }

  async function stopRecording() {
    clearInterval(state.timerInterval);
    state.recState = "transcribing";
    $("#record-btn").className = "record-btn is-transcribing";
    $("#record-icon").className = "record-icon";
    $("#record-status").textContent = "Transcription en cours…";

    let result;
    try {
      result = await api("/api/record/stop", { method: "POST" });
    } catch (err) {
      $("#record-status").textContent = err.message;
      resetRecordUI();
      return;
    }
    pollUntilDone(result.id);
  }

  function pollUntilDone(courseId) {
    clearInterval(state.pollInterval);
    state.pollInterval = setInterval(async () => {
      const course = await api(`/api/courses/${courseId}`).catch(() => null);
      if (!course) return;
      if (course.statut === "done" || course.statut === "error") {
        clearInterval(state.pollInterval);
        if (course.statut === "error") {
          $("#record-status").textContent = "Erreur : " + (course.erreur || "inconnue");
          $("#record-btn").className = "record-btn";
          $("#subject-select").disabled = false;
        } else {
          goLibrary();
        }
      }
    }, 1500);
  }

  // --- Détail d'un cours ---------------------------------------------------

  async function selectCourse(id) {
    const course = await api(`/api/courses/${id}`).catch((err) => {
      $("#empty-library").hidden = false;
      $("#empty-library").textContent = err.message;
      return null;
    });
    if (!course) return;

    state.currentId = id;
    state.activeTab = "transcription";
    showScreen("detail");

    $("#detail-subject-title").textContent = course.matiere_titre;
    $("#detail-meta").textContent = `${course.titre} · ${formatDate(course.date)}`;
    $("#transcription-text").textContent = course.transcription ||
      (course.statut === "transcribing" ? "Transcription en cours…" : "(vide)");

    switchTab("transcription");
    renderSlides(course);
    renderPaper("fiche", course.fiche_pdf, id);
    renderPaper("exercices", course.exercices_pdf, id);
  }

  function renderSlides(course) {
    const grid = $("#slides-grid");
    grid.innerHTML = "";
    for (const page of course.slides_pages) {
      const thumb = document.createElement("div");
      thumb.className = "slide-thumb";
      const img = document.createElement("img");
      img.src = `/api/courses/${course.id}/file/slides/${page}`;
      img.loading = "lazy";
      thumb.appendChild(img);
      grid.appendChild(thumb);
    }
  }

  function renderPaper(kind, ready, courseId) {
    const paper = $(`#${kind}-paper`);
    const empty = $(`#${kind}-empty`);
    const embed = $(`#${kind}-embed`);
    if (ready) {
      paper.hidden = false;
      empty.hidden = true;
      embed.src = `/api/courses/${courseId}/file/${kind}.pdf`;
    } else {
      paper.hidden = true;
      empty.hidden = false;
      embed.removeAttribute("src");
    }
  }

  async function deleteCurrentCourse() {
    if (!state.currentId) return;
    if (!confirm("Supprimer définitivement ce cours (audio, transcription, fiche) ?")) return;
    try {
      await api(`/api/courses/${state.currentId}`, { method: "DELETE" });
      goLibrary();
    } catch (err) {
      alert(err.message);
    }
  }

  function switchTab(name) {
    state.activeTab = name;
    $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
    $$(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === `tab-${name}`));
  }

  // --- Slides upload ---------------------------------------------------

  async function uploadSlides(file) {
    if (!state.currentId || !file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      alert("Seuls les fichiers PDF sont acceptés.");
      return;
    }
    const form = new FormData();
    form.append("file", file);
    try {
      await api(`/api/courses/${state.currentId}/slides`, { method: "POST", body: form });
      selectCourse(state.currentId);
    } catch (err) {
      alert(err.message);
    }
  }

  async function copyPrompt(kind) {
    if (!state.currentId) return;
    let text;
    try {
      ({ prompt: text } = await api(`/api/courses/${state.currentId}/prompt-fiche`));
    } catch (err) {
      alert(err.message);
      return;
    }
    const hint = document.querySelector(`.copied-hint[data-hint="${kind}"]`);
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      window.prompt("Copie cette demande (Cmd+C) et colle-la dans Claude Code :", text);
    }
    if (hint) {
      hint.hidden = false;
      setTimeout(() => { hint.hidden = true; }, 1500);
    }
  }

  // --- Setup ---------------------------------------------------

  function setup() {
    $("#tl-close").addEventListener("click", closeWindow);
    $("#tl-minimize").addEventListener("click", () => callWindowAPI("minimize"));
    $("#tl-zoom").addEventListener("click", () => callWindowAPI("toggle_fullscreen"));

    // Filet de sécurité : la fenêtre est frameless, Cmd+W ne fonctionne pas par défaut.
    document.addEventListener("keydown", (e) => {
      if (e.metaKey && e.key.toLowerCase() === "w") {
        e.preventDefault();
        closeWindow();
      }
    });

    $("#new-course-btn").addEventListener("click", goRecording);
    $("#search").addEventListener("input", (e) => {
      state.search = e.target.value;
      renderLibrary();
    });

    $("#back-to-library-from-recording").addEventListener("click", goLibrary);
    $("#back-to-library-from-detail").addEventListener("click", goLibrary);

    $("#subject-select").addEventListener("change", (e) => {
      state.selectedSubjectCode = e.target.value;
    });

    $("#record-btn").addEventListener("click", () => {
      if (state.recState === "idle") startRecording();
      else if (state.recState === "recording") stopRecording();
    });

    $("#delete-course-btn").addEventListener("click", deleteCurrentCourse);

    $$(".tab").forEach((tab) =>
      tab.addEventListener("click", () => switchTab(tab.dataset.tab))
    );

    $$(".copy-prompt-btn").forEach((btn) =>
      btn.addEventListener("click", () => copyPrompt(btn.dataset.target))
    );

    const dropzone = $("#slides-dropzone");
    const slidesInput = $("#slides-input");
    slidesInput.addEventListener("change", () => uploadSlides(slidesInput.files[0]));
    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      uploadSlides(e.dataTransfer.files[0]);
    });

    loadSubjects().then(loadCourses);
  }

  document.addEventListener("DOMContentLoaded", setup);
})();
