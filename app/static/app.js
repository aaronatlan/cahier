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
    generationPollIntervals: {}, // kind -> interval id
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

  async function goRecording() {
    showScreen("recording");
    resetRecordUI();
    // Si un enregistrement tourne déjà côté serveur (ex. l'utilisateur a navigué
    // ailleurs sans arrêter), on se raccroche dessus au lieu de perdre tout accès
    // à un bouton Stop fonctionnel pendant que le micro continue de tourner.
    const status = await api("/api/record/status").catch(() => null);
    if (status && status.recording) {
      enterRecordingUI(status.elapsed_sec || 0);
    }
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
        if (session.resume_ok) badges.appendChild(makeBadge("Résumé", true));
        if (session.fiche_pdf) badges.appendChild(makeBadge("Fiche", true));
        if (session.exercices_pdf) badges.appendChild(makeBadge("Exercices", true));

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

  // Mini-rendu markdown pour resume.md : volontairement minimal (##, listes à puces
  // avec sous-puces indentées, **gras**) puisque c'est nous qui contrôlons ce que
  // Claude Code écrit dans ce fichier (voir CLAUDE.md > Résumé).
  function renderMarkdown(md) {
    const inline = (text) =>
      escapeHtml(text).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

    const lines = md.replace(/\r\n/g, "\n").split("\n");
    let html = "";
    let inList = false;

    const closeList = () => {
      if (inList) {
        html += "</ul>";
        inList = false;
      }
    };

    for (const rawLine of lines) {
      const line = rawLine.trimEnd();
      const heading = /^(#{1,6})\s*(.*)$/.exec(line);
      const bullet = /^(\s*)[-*]\s+(.*)$/.exec(line);

      if (heading) {
        closeList();
        const tag = heading[1].length <= 2 ? "h2" : "h3";
        html += `<${tag}>${inline(heading[2])}</${tag}>`;
      } else if (bullet) {
        if (!inList) {
          html += "<ul>";
          inList = true;
        }
        const isSub = bullet[1].length > 0;
        html += `<li${isSub ? ' class="sub"' : ""}>${inline(bullet[2])}</li>`;
      } else if (line.trim() === "") {
        closeList();
      } else {
        closeList();
        html += `<p>${inline(line.trim())}</p>`;
      }
    }
    closeList();
    return html;
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

  function enterRecordingUI(elapsedSec) {
    state.recState = "recording";
    state.recordStartedAt = Date.now() - elapsedSec * 1000;
    $("#record-btn").className = "record-btn is-recording";
    $("#record-icon").className = "record-icon is-recording";
    $("#record-status").textContent = "Enregistrement…";
    $("#subject-select").disabled = true;
    tick();
    clearInterval(state.timerInterval);
    state.timerInterval = setInterval(tick, 500);
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
    enterRecordingUI(0);
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
      resetRecordUI();
      $("#record-status").textContent = err.message;
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
    renderDetailTitre(course.titre);
    $("#detail-date").textContent = formatDate(course.date);
    $("#transcription-text").textContent = course.transcription ||
      (course.statut === "transcribing" ? "Transcription en cours…" : "(vide)");

    switchTab("transcription");
    renderResume(course);
    renderSlides(course);
    renderPaper("fiche", course.fiche_pdf, id);
    renderPaper("exercices", course.exercices_pdf, id);

    // Si des générations sont déjà en cours pour ce cours (ex. lancées puis on a
    // navigué ailleurs), se raccrocher dessus plutôt que de perdre le suivi.
    for (const kind of GENERATION_KINDS) {
      const genStatus = await api(`/api/courses/${id}/generate/${kind}/status`).catch(() => null);
      if (genStatus && genStatus.state === "running") {
        setGenerationUI(kind, true);
        pollGeneration(kind, id);
      } else {
        setGenerationUI(kind, false);
      }
    }
  }

  function renderResume(course) {
    const ready = Boolean(course.resume);
    setReadyState($("#resume-text"), $("#resume-empty"), ready);
    if (ready) $("#resume-text").innerHTML = renderMarkdown(course.resume);
  }

  // --- Titre du cours (édition inline) -----------------------------------

  function renderDetailTitre(titre) {
    const span = document.createElement("span");
    span.id = "detail-titre";
    span.className = "detail-titre-editable";
    span.title = "Cliquer pour renommer";
    span.textContent = titre;
    span.addEventListener("click", () => editDetailTitre(titre));
    $("#detail-titre").replaceWith(span);
  }

  function editDetailTitre(current) {
    const input = document.createElement("input");
    input.id = "detail-titre";
    input.type = "text";
    input.className = "detail-titre-input";
    input.value = current;
    $("#detail-titre").replaceWith(input);
    input.focus();
    input.select();

    let settled = false;
    const commit = async () => {
      if (settled) return;
      settled = true;
      const newTitre = input.value.trim() || current;
      if (newTitre === current) {
        renderDetailTitre(current);
        return;
      }
      try {
        await api(`/api/courses/${state.currentId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ titre: newTitre }),
        });
        const course = state.courses.find((c) => c.id === state.currentId);
        if (course) course.titre = newTitre;
        renderDetailTitre(newTitre);
      } catch (err) {
        alert(err.message);
        renderDetailTitre(current);
      }
    };
    input.addEventListener("blur", commit);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") input.blur();
      if (e.key === "Escape") {
        settled = true;
        renderDetailTitre(current);
      }
    });
  }

  // --- Slides --------------------------------------------------------

  function renderSlides(course) {
    const grid = $("#slides-grid");
    grid.innerHTML = "";
    course.slides_pages.forEach((page, index) => {
      const thumb = document.createElement("div");
      thumb.className = "slide-thumb";
      thumb.addEventListener("click", () => openSlideViewer(course.id, course.slides_pages, index));

      const img = document.createElement("img");
      img.src = `/api/courses/${course.id}/file/slides/${page}`;
      img.loading = "lazy";
      thumb.appendChild(img);

      const delBtn = document.createElement("button");
      delBtn.className = "slide-delete-btn";
      delBtn.textContent = "✕";
      delBtn.title = "Supprimer cette page";
      delBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        deleteSlidePage(course.id, page);
      });
      thumb.appendChild(delBtn);

      grid.appendChild(thumb);
    });
    $("#slides-toolbar").hidden = course.slides_pages.length === 0;
  }

  async function refreshCourse(id) {
    const course = await api(`/api/courses/${id}`).catch((err) => {
      alert(err.message);
      return null;
    });
    if (!course) return null;
    const idx = state.courses.findIndex((c) => c.id === id);
    if (idx !== -1) state.courses[idx] = course;
    return course;
  }

  async function deleteAllSlides(courseId) {
    if (!confirm("Supprimer toutes les slides de ce cours ?")) return;
    try {
      await api(`/api/courses/${courseId}/slides`, { method: "DELETE" });
    } catch (err) {
      alert(err.message);
      return;
    }
    const course = await refreshCourse(courseId);
    if (course) renderSlides(course);
  }

  async function deleteSlidePage(courseId, pageFilename) {
    const match = /page-(\d+)\.png$/.exec(pageFilename);
    if (!match) return;
    const pageNumber = parseInt(match[1], 10);
    try {
      await api(`/api/courses/${courseId}/slides/${pageNumber}`, { method: "DELETE" });
    } catch (err) {
      alert(err.message);
      return;
    }
    const course = await refreshCourse(courseId);
    if (course) renderSlides(course);
  }

  // --- Visionneuse de slides -------------------------------------------

  let viewerCourseId = null;
  let viewerPages = [];
  let viewerIndex = 0;

  function openSlideViewer(courseId, pages, index) {
    viewerCourseId = courseId;
    viewerPages = pages;
    viewerIndex = index;
    renderSlideViewer();
    $("#slide-viewer").hidden = false;
  }

  function closeSlideViewer() {
    $("#slide-viewer").hidden = true;
    $("#slide-viewer-img").src = "";
  }

  function stepSlideViewer(delta) {
    const next = viewerIndex + delta;
    if (next < 0 || next >= viewerPages.length) return;
    viewerIndex = next;
    renderSlideViewer();
  }

  function renderSlideViewer() {
    const page = viewerPages[viewerIndex];
    $("#slide-viewer-img").src = `/api/courses/${viewerCourseId}/file/slides/${page}`;
    $("#slide-viewer-counter").textContent = `${viewerIndex + 1} / ${viewerPages.length}`;
    $("#slide-viewer-prev").disabled = viewerIndex === 0;
    $("#slide-viewer-next").disabled = viewerIndex === viewerPages.length - 1;
  }

  function renderPaper(kind, ready, courseId) {
    const embed = $(`#${kind}-embed`);
    setReadyState($(`#${kind}-paper`), $(`#${kind}-empty`), ready);
    if (ready) {
      embed.src = `/api/courses/${courseId}/file/${kind}.pdf`;
    } else {
      embed.removeAttribute("src");
    }
  }

  function setReadyState(shownEl, emptyEl, ready) {
    shownEl.hidden = !ready;
    emptyEl.hidden = ready;
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

  // --- Génération résumé/fiche/exercices (via le CLI Claude Code) --------
  // Chaque onglet déclenche uniquement son propre livrable (/resume, /fiche,
  // /exercices), indépendamment des deux autres.

  const GENERATION_KINDS = ["resume", "fiche", "exercices"];

  function setGenerationUI(kind, generating, message) {
    $$(`.generate-btn[data-kind="${kind}"]`).forEach((btn) => {
      btn.disabled = generating;
      btn.textContent = generating ? "Génération en cours…" : "Générer avec Claude Code";
    });
    $$(`.generate-status[data-kind="${kind}"]`).forEach((el) => {
      el.hidden = !message;
      el.textContent = message || "";
    });
  }

  async function startGeneration(kind) {
    if (!state.currentId) return;
    const courseId = state.currentId;
    try {
      await api(`/api/courses/${courseId}/generate/${kind}`, { method: "POST" });
    } catch (err) {
      alert(err.message);
      return;
    }
    setGenerationUI(kind, true);
    pollGeneration(kind, courseId);
  }

  function pollGeneration(kind, courseId) {
    clearInterval(state.generationPollIntervals[kind]);
    state.generationPollIntervals[kind] = setInterval(async () => {
      const status = await api(`/api/courses/${courseId}/generate/${kind}/status`).catch(() => null);
      if (!status || status.state === "running") return;
      clearInterval(state.generationPollIntervals[kind]);
      if (state.currentId !== courseId) return;
      if (status.state === "error") {
        setGenerationUI(
          kind, false,
          `Échec de la génération (voir generation-${kind}.log dans le dossier du cours).`
        );
        return;
      }
      setGenerationUI(kind, false);
      const course = await refreshCourse(courseId);
      if (course) {
        renderResume(course);
        renderPaper("fiche", course.fiche_pdf, courseId);
        renderPaper("exercices", course.exercices_pdf, courseId);
      }
    }, 3000);
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

    $$(".generate-btn").forEach((btn) =>
      btn.addEventListener("click", () => startGeneration(btn.dataset.kind))
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

    $("#delete-slides-btn").addEventListener("click", () => deleteAllSlides(state.currentId));

    $("#slide-viewer-close").addEventListener("click", closeSlideViewer);
    $("#slide-viewer-prev").addEventListener("click", () => stepSlideViewer(-1));
    $("#slide-viewer-next").addEventListener("click", () => stepSlideViewer(1));
    $("#slide-viewer").addEventListener("click", (e) => {
      if (e.target.id === "slide-viewer") closeSlideViewer();
    });
    document.addEventListener("keydown", (e) => {
      if ($("#slide-viewer").hidden) return;
      if (e.key === "Escape") closeSlideViewer();
      else if (e.key === "ArrowLeft") stepSlideViewer(-1);
      else if (e.key === "ArrowRight") stepSlideViewer(1);
    });

    loadSubjects().then(loadCourses);
  }

  document.addEventListener("DOMContentLoaded", setup);
})();
