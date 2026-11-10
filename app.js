(() => {
  "use strict";

  const cfg = window.SJA_CONFIG || {};
  const configured =
    cfg.SUPABASE_URL &&
    cfg.SUPABASE_ANON_KEY &&
    cfg.SUPABASE_URL.startsWith("https://") &&
    !cfg.SUPABASE_URL.includes("PASTE_") &&
    !cfg.SUPABASE_ANON_KEY.includes("PASTE_");

  const supabase =
    configured && window.supabase
      ? window.supabase.createClient(
          cfg.SUPABASE_URL,
          cfg.SUPABASE_ANON_KEY
        )
      : null;

  const $ = (s, root = document) => root.querySelector(s);

  const grid = $("#jobGrid");
  const notice = $("#setupNotice");
  const count = $("#resultCount");
  const detailDialog = $("#detailDialog");
  const adminDialog = $("#adminDialog");

  let allJobs = [];
  let activeCategory = "All";
  let searchTerm = "";
  let currentUser = null;
  let editingId = null;
  let showAllJobs = false;

  function displayCategory(value) {
    const category = String(value || "").trim();

    if (["Latest Jobs", "Vacancy", "Jobs"].includes(category)) {
      return "Vacancy";
    }

    if (["Results", "Result", "Answer Key"].includes(category)) {
      return "Result";
    }

    return category || "Vacancy";
  }

  $("#year").textContent = new Date().getFullYear();

  function escapeHtml(value = "") {
    return String(value).replace(/[&<>"']/g, c => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    }[c]));
  }

  function formatDate(value) {
    if (!value) return "As per notification";

    const date = new Date(
      value + (String(value).length === 10 ? "T00:00:00" : "")
    );

    if (Number.isNaN(date.getTime())) return String(value);

    return date.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric"
    });
  }

  function isExpired(job) {
    return job.last_date &&
      new Date(job.last_date + "T23:59:59") < new Date();
  }

  function isNewJob(job) {
    if (!job.created_at) return false;

    const created = new Date(job.created_at).getTime();

    return Number.isFinite(created) &&
      Date.now() - created >= 0 &&
      Date.now() - created < 3 * 24 * 60 * 60 * 1000;
  }

  const demoJobs = [];


  // Homepage live ticker: latest published jobs + School & Exam Guide articles.
  const TICKER_CACHE_KEY = "sja_latest_govt_updates_v3";
  const tickerTrack = document.getElementById("sjaBreakingTrack");

  function tickerCategoryHindi(value) {
    if (value === "study_guide") return "एग्जाम गाइड";
    const c = displayCategory(value);
    if (c === "Admit Card") return "एडमिट कार्ड";
    if (c === "Result") return "रिजल्ट";
    return "सरकारी भर्ती";
  }

  function escapeTicker(value) {
    return String(value ?? "").replace(/[&<>"']/g, ch => ({
      "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
    }[ch]));
  }

  function paintTicker(items) {
    if (!tickerTrack) return;
    const valid = (Array.isArray(items) ? items : [items]).filter(item => item?.title);
    if (!valid.length) return;
    const makeLinks = () => valid.map(item => {
      const isGuide = item.ticker_type === "study_guide";
      const href = isGuide
        ? `education.html#article-${encodeURIComponent(item.id)}`
        : `?job=${encodeURIComponent(item.id)}`;
      return `<a href="${href}" aria-label="Open ${escapeTicker(item.title)}">${escapeTicker(tickerCategoryHindi(isGuide ? "study_guide" : item.category))}: ${escapeTicker(item.title)}</a>`;
    }).join("");
    tickerTrack.innerHTML = makeLinks() + makeLinks();
  }

  function readTickerCache() {
    try {
      const raw = localStorage.getItem(TICKER_CACHE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (_) { return null; }
  }

  async function refreshGovernmentTicker() {
    const cached = readTickerCache();
    if (cached?.length) paintTicker(cached);
    if (!supabase) return;
    try {
      const [jobsResult, guidesResult] = await Promise.all([
        supabase.from("jobs")
          .select("id,title,category,created_at")
          .eq("status", "published")
          .order("created_at", { ascending: false })
          .limit(5),
        supabase.from("school_articles")
          .select("id,title,article_type,published_at")
          .eq("status", "published")
          .eq("article_type", "study_guide")
          .order("published_at", { ascending: false })
          .limit(5)
      ]);

      if (jobsResult.error) throw jobsResult.error;
      // School & Exam Guide is a separate table; if its table/policy is unavailable,
      // keep the job ticker working rather than hiding all updates.
      const jobs = (jobsResult.data || []).filter(item => item?.title)
        .map(item => ({ ...item, ticker_type: "job" }));
      const guides = guidesResult.error ? [] : (guidesResult.data || [])
        .filter(item => item?.title)
        .map(item => ({ ...item, category: "study_guide", ticker_type: "study_guide" }));
      const latest = [...jobs, ...guides]
        .sort((a, b) => new Date(b.published_at || b.created_at || 0) - new Date(a.published_at || a.created_at || 0))
        .slice(0, 5);

      if (latest.length) {
        try { localStorage.setItem(TICKER_CACHE_KEY, JSON.stringify(latest)); } catch (_) {}
        paintTicker(latest);
      }
    } catch (error) {
      console.warn("Government updates ticker refresh skipped:", error);
    }
  }

  refreshGovernmentTicker();
  window.setInterval(refreshGovernmentTicker, 5 * 60 * 1000);

  function toast(message) {
    // Admin dialog is a browser top-layer element. Keep the diagnostic inside it
    // so it remains visible while the modal is open and after adminRoot rerenders.
    const adminStatus = $("#adminPushStatus");
    if (adminStatus && adminDialog?.open) {
      adminStatus.hidden = false;
      adminStatus.textContent = message;
      adminStatus.style.display = "block";
    }

    let el = $("#toast");
    if (!el) {
      el = document.createElement("div");
      el.id = "toast";
      document.body.appendChild(el);
    } else if (el.parentElement !== document.body) {
      document.body.appendChild(el);
    }

    Object.assign(el.style, {
      position: "fixed",
      left: "50%",
      bottom: "24px",
      transform: "translateX(-50%)",
      zIndex: "99999",
      maxWidth: "min(92vw, 560px)",
      padding: "12px 18px",
      borderRadius: "10px",
      background: "#172033",
      color: "#fff",
      boxShadow: "0 8px 28px rgba(0,0,0,.25)",
      fontSize: "14px",
      lineHeight: "1.45",
      display: "block",
      opacity: "1"
    });

    el.textContent = message;
    el.classList.add("show");
    clearTimeout(el._sjaToastTimer);
    el._sjaToastTimer = setTimeout(() => {
      el.classList.remove("show");
      el.style.display = "none";
    }, 7000);
    el.style.display = "block";
  }

  async function loadJobs() {
    if (!supabase) {
      if (notice) {
        notice.hidden = false;
        notice.textContent = "Live updates abhi load nahi ho paaye. Kripya thodi der baad dobara try karein.";
      }
      allJobs = [];
      renderJobs();
      return;
    }

    const { data, error } = await supabase
      .from("jobs")
      .select("*")
      .eq("status", "published")
      .order("created_at", { ascending: false });

    if (error) {
      if (notice) {
        notice.hidden = false;
        notice.textContent =
          "Live database se connect nahi ho paya. Supabase settings aur policies check karein.";
      }

      allJobs = [];
      renderJobs();
      return;
    }

    if (notice) notice.hidden = true;

    allJobs = data || [];
    renderJobs();
    openSharedJobFromUrl();
  }

  function renderJobs() {
    if (!grid || !count) return;

    const filtered = allJobs.filter(job => {
      const category = displayCategory(job.category);

      const categoryMatches =
        activeCategory === "All" ||
        category === activeCategory;

      const text = [
        job.title,
        job.department,
        job.qualification,
        job.result_status
      ].filter(Boolean).join(" ").toLowerCase();

      return categoryMatches && text.includes(searchTerm);
    });

    count.textContent =
      `${filtered.length} update${filtered.length === 1 ? "" : "s"}`;

    const heading = $("#listingHeading");

    if (heading) {
      heading.textContent =
        activeCategory === "All" ? "Latest Updates" : activeCategory;
    }

    const visible = showAllJobs ? filtered : filtered.slice(0, 8);
    const more = $("#showMoreJobs");

    if (more) {
      more.hidden = filtered.length <= 8 || showAllJobs;
      more.textContent =
        `Show More Jobs (${Math.max(0, filtered.length - 8)} aur)`;
    }

    if (!filtered.length) {
      grid.innerHTML = `
        <div class="empty-state">
          <strong>Abhi koi matching update nahi mila.</strong>
          <br>
          <span>Search badal kar dekhein ya baad mein check karein.</span>
        </div>`;
      return;
    }

    grid.innerHTML = visible.map(job => {
      const category = displayCategory(job.category);

      let label1;
      let value1;
      let label2;
      let value2;
      let mainUrl;
      let buttonText;

      if (category === "Admit Card") {
        label1 = "Exam Date";
        value1 = formatDate(job.exam_date);

        label2 = "Admit Card Release Date";
        value2 = formatDate(job.admit_card_release_date);

        mainUrl = job.admit_card_url;
        buttonText = "Download Admit Card ↗";
      } else if (category === "Result") {
        label1 = "Result Date";
        value1 = formatDate(job.result_date);

        label2 = "Result Status";
        value2 = job.result_status || "Check official result";

        mainUrl = job.result_url;
        buttonText = "Check Result ↗";
      } else {
        label1 = "Vacancies";
        value1 = job.vacancies || "See notification";

        label2 = "Last Date to Apply";
        value2 = formatDate(job.last_date);

        mainUrl = job.apply_url;
        buttonText = "Apply Online ↗";
      }

      return `
        <article class="job-card">
          <div class="card-top">
            <span class="tag">${escapeHtml(category)}</span>
            <span class="status-tag">
              ${isExpired(job) ? "Date passed" : "Check details"}
            </span>
          </div>

          <h3>
            ${escapeHtml(job.title)}
            ${isNewJob(job) ? ' <span class="new-badge">NEW</span>' : ""}
          </h3>

          <p class="department">
            ${escapeHtml(job.department || "Department not specified")}
          </p>

          <div class="card-meta">
            <div class="meta-item">
              <small>${escapeHtml(label1)}</small>
              <strong>${escapeHtml(value1)}</strong>
            </div>

            <div class="meta-item">
              <small>${escapeHtml(label2)}</small>
              <strong>${escapeHtml(value2)}</strong>
            </div>
          </div>

          <div class="card-actions">
  <button class="details-btn"
          data-detail="${escapeHtml(job.id)}">
    View Details
  </button>

  ${
    mainUrl
      ? `<a class="apply-btn"
            href="${escapeHtml(mainUrl)}"
            target="_blank"
            rel="noopener noreferrer">
           ${buttonText}
         </a>`
      : `<button class="apply-btn"
                 data-detail="${escapeHtml(job.id)}">
           View Update
         </button>`
  }

  <button type="button"
          class="share-btn"
          data-share-job="${escapeHtml(job.id)}">
    ↗ Share
  </button>


</div>
        </article>`;
    }).join("");
  }

  function showDetails(id) {
    const job = allJobs.find(item => String(item.id) === String(id));
    if (!job) return;

    const category = displayCategory(job.category);
    const rows = [];
    let hiddenUnclearFields = 0;

    // Keep the original notice language. Do not translate source facts.
    const sourceText = [job.title, job.description, job.qualification, job.fees,
      job.age_limit, job.selection_process].filter(Boolean).join(" ");
    const hindi = /[\u0900-\u097F]/.test(sourceText);
    const L = hindi ? {
      total: "कुल पद", qualification: "योग्यता", noticeDate: "अधिसूचना की तारीख",
      lastDate: "आवेदन की अंतिम तारीख", dob: "जन्मतिथि पात्रता",
      fees: "आवेदन शुल्क", age: "आयु सीमा", selection: "चयन प्रक्रिया",
      notification: "आधिकारिक अधिसूचना", apply: "ऑनलाइन आवेदन",
      examDate: "परीक्षा की तारीख", admitDate: "प्रवेश पत्र जारी होने की तारीख",
      downloadAdmit: "प्रवेश पत्र डाउनलोड करें", resultDate: "परिणाम की तारीख",
      resultStatus: "परिणाम की स्थिति", checkResult: "परिणाम देखें",
      cutoff: "कट-ऑफ विवरण", merit: "मेरिट सूची", department: "विभाग की जानकारी उपलब्ध नहीं",
      complete: "पूरी जानकारी", verify: "आधिकारिक अधिसूचना में जाँचें",
      unavailable: "विस्तृत जानकारी अभी उपलब्ध नहीं है। कृपया आधिकारिक अधिसूचना देखें।",
      badText: "इस पोस्ट की कुछ जानकारी मूल सूचना से साफ़ नहीं पढ़ी जा सकी। सही जानकारी के लिए आधिकारिक अधिसूचना देखें।",
      dates: "आवेदन करने से पहले तारीखों और लिंक की पुष्टि आधिकारिक वेबसाइट पर करें।"
    } : {
      total: "Total Vacancies", qualification: "Qualification", noticeDate: "Notification Date",
      lastDate: "Last Date to Apply", dob: "DOB Eligibility", fees: "Application Fees",
      age: "Age Limit", selection: "Selection Process", notification: "Official Notification",
      apply: "Apply Online", examDate: "Exam Date", admitDate: "Admit Card Release Date",
      downloadAdmit: "Download Admit Card", resultDate: "Result Date", resultStatus: "Result Status",
      checkResult: "Check Result", cutoff: "Cut-off Details", merit: "Merit List",
      department: "Department not specified", complete: "Complete Details",
      verify: "Check official notification", unavailable: "Detailed information is not available yet. Please check the official notification.",
      badText: "Some details could not be read clearly from the original notice. Please open the official notification to verify them.",
      dates: "Verify dates and links on the official website before applying."
    };

    function readableValue(value) {
      if (value === null || value === undefined || value === "") return "";
      const text = String(value).replace(/\s+/g, " ").trim();
      const broken = /[�\uFFFD]|Ã.|Â.|â€|â€™|â€œ|\bpage\s+\d+\s+of\s+\d+\b|\bfor the post\b/i.test(text);
      if (broken || text.length > 260) {
        hiddenUnclearFields++;
        return L.verify;
      }
      return text;
    }

    function readableDescription(value) {
      const raw = String(value || "").replace(/\r/g, "").trim();
      if (!raw) return L.unavailable;
      const parts = raw.split(/(?<=[.!?।])\s+/).filter(Boolean);
      const good = parts.filter(part =>
        !/[�\uFFFD]|Ã.|Â.|â€|â€™|â€œ|\bpage\s+\d+\s+of\s+\d+\b/i.test(part) &&
        !/This automatically collected entry is saved as a draft/i.test(part)
      );
      if (good.length !== parts.length) hiddenUnclearFields++;
      return good.length ? good.map(part => `<p>${escapeHtml(part)}</p>`).join("") : L.badText;
    }

    function addRow(label, value) {
      if (value === null || value === undefined || value === "") return;
      value = readableValue(value);
      rows.push(`<tr><th>${escapeHtml(label)}</th><td>${escapeHtml(value)}</td></tr>`);
    }

    function addLink(label, url) {
      if (!url) return;
      rows.push(`<tr><th>${escapeHtml(label)}</th><td><a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)} ↗</a></td></tr>`);
    }

    if (category === "Vacancy") {
      addRow(L.total, job.vacancies);
      addRow(L.qualification, job.qualification);
      addRow(L.noticeDate, formatDate(job.notification_date));
      addRow(L.lastDate, formatDate(job.last_date));
      if (job.dob_from || job.dob_to) addRow(L.dob, `${job.dob_from ? formatDate(job.dob_from) : "—"} से ${job.dob_to ? formatDate(job.dob_to) : "—"}`);
      addRow(L.fees, job.fees);
      addRow(L.age, job.age_limit);
      addRow(L.selection, job.selection_process);
      addLink(L.notification, job.notification_url);
      addLink(L.apply, job.apply_url);
    }

    if (category === "Admit Card") {
      addRow(L.examDate, formatDate(job.exam_date));
      addRow(L.admitDate, formatDate(job.admit_card_release_date));
      addLink(L.downloadAdmit, job.admit_card_url);
      addLink(L.notification, job.notification_url);
    }

    if (category === "Result") {
      addRow(L.resultDate, formatDate(job.result_date));
      addRow(L.resultStatus, job.result_status || (hindi ? "आधिकारिक सूचना देखें" : "See official notification"));
      addLink(L.checkResult, job.result_url);
      addRow(L.cutoff, job.cutoff_details || job.cutoff || "");
      addLink(L.merit, job.merit_list_url);
      addLink(L.notification, job.notification_url);
    }

    $("#detailContent").innerHTML = `
      <span class="tag">${escapeHtml(category)}</span>
      <h2 class="detail-title">${escapeHtml(job.title)}</h2>
      <p class="detail-dept">${escapeHtml(job.department || L.department)}</p>
      <table class="detail-table detail-info-list"><tbody>${rows.join("")}</tbody></table>
      <h3 class="detail-section-heading">${L.complete}</h3>
      <div class="detail-copy">${readableDescription(job.description)}</div>
      ${hiddenUnclearFields ? `<p class="detail-quality-note">⚠️ ${L.badText}</p>` : ""}
      <p class="tiny-note">${L.dates}</p>
    `;

    updateJobSeo(job);
    detailDialog.showModal();
  }

  function updateJobSeo(job) {
    if (!job) return;
    const url = new URL(window.location.href);
    url.searchParams.set("job", String(job.id));
    url.hash = "";
    window.history.replaceState({}, "", url.toString());

    const title = `${job.title} | Sarkari Job Alert`;
    document.title = title;

    let description = String(job.description || `${job.title} की पूरी जानकारी, योग्यता, महत्वपूर्ण तिथियां और आधिकारिक आवेदन लिंक देखें।`)
      .replace(/\s+/g, " ").trim();
    if (description.length > 155) description = description.slice(0, 152).trimEnd() + "...";

    let descriptionTag = document.querySelector('meta[name="description"]');
    if (!descriptionTag) {
      descriptionTag = document.createElement("meta");
      descriptionTag.name = "description";
      document.head.appendChild(descriptionTag);
    }
    descriptionTag.content = description;

    let canonical = document.querySelector('link[rel="canonical"]');
    if (!canonical) {
      canonical = document.createElement("link");
      canonical.rel = "canonical";
      document.head.appendChild(canonical);
    }
    canonical.href = url.toString();

    const setMeta = (selector, value) => {
      let tag = document.querySelector(selector);
      if (!tag) {
        tag = document.createElement("meta");
        const match = selector.match(/\[(name|property)="([^"]+)"\]/);
        if (match) tag.setAttribute(match[1], match[2]);
        document.head.appendChild(tag);
      }
      tag.setAttribute("content", value);
    };
    setMeta('meta[property="og:title"]', title);
    setMeta('meta[property="og:description"]', description);
    setMeta('meta[property="og:url"]', url.toString());
    setMeta('meta[name="twitter:title"]', title);
    setMeta('meta[name="twitter:description"]', description);

    let robots = document.querySelector('meta[name="robots"]');
    if (!robots) {
      robots = document.createElement("meta");
      robots.name = "robots";
      document.head.appendChild(robots);
    }
    robots.content = "index,follow,max-image-preview:large";
  }

  function resetHomeSeo() {
    document.title = "Sarkari Job Alert — Latest Govt Jobs, Admit Card & Results";
    const canonical = document.querySelector('link[rel="canonical"]');
    if (canonical) canonical.href = "https://sarkari-jobalert.com/";
    const description = document.querySelector('meta[name="description"]');
    if (description) description.content = "Sarkari Job Alert (SarkariJobAlert) par latest sarkari naukri, government job notifications, admit cards, results aur answer keys ki verified updates paayen.";
    const homeTitle = "Sarkari Job Alert — Latest Govt Jobs, Admit Card & Results";
    const homeDescription = "Sarkari Job Alert (SarkariJobAlert) par latest sarkari naukri, government job notifications, admit cards, results aur answer keys ki verified updates paayen.";
    const ogTitle = document.querySelector('meta[property="og:title"]');
    if (ogTitle) ogTitle.content = homeTitle;
    const ogDescription = document.querySelector('meta[property="og:description"]');
    if (ogDescription) ogDescription.content = homeDescription;
    const ogUrl = document.querySelector('meta[property="og:url"]');
    if (ogUrl) ogUrl.content = "https://sarkari-jobalert.com/";
    const twitterTitle = document.querySelector('meta[name="twitter:title"]');
    if (twitterTitle) twitterTitle.content = homeTitle;
    const twitterDescription = document.querySelector('meta[name="twitter:description"]');
    if (twitterDescription) twitterDescription.content = homeDescription;
    const url = new URL(window.location.href);
    url.searchParams.delete("job");
    window.history.replaceState({}, "", url.pathname + url.search + url.hash);
  }

function openSharedJobFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const jobId = params.get("job");

  if (!jobId) return;

  const job = allJobs.find(
    item => String(item.id) === String(jobId)
  );

  if (job) {
    showDetails(job.id);
  }
}
  function getJobShareData(id) {
  const job = allJobs.find(
    item => String(item.id) === String(id)
  );

  if (!job) return null;

  const url = new URL(window.location.href);
  url.searchParams.set("job", String(job.id));
  url.hash = "";

  const shareUrl = url.toString();

  const message =
    `${job.title}\n` +
    `${job.department || ""}\n` +
    `Category: ${displayCategory(job.category)}\n` +
    `Details: ${shareUrl}`;

  return {
    title: job.title,
    text: message,
    url: shareUrl
  };
}

document.addEventListener("click", event => {
  const shareButton = event.target.closest("[data-share-job]");

  if (shareButton) {
    const data = getJobShareData(shareButton.dataset.shareJob);
    if (!data) return;

    if (navigator.share) {
      navigator.share({
        title: data.title,
        text: data.text,
        url: data.url
      }).catch(() => {});
    } else {
      window.open(
        "https://wa.me/?text=" + encodeURIComponent(data.text),
        "_blank",
        "noopener,noreferrer"
      );
    }
    return;
  }



  const button = event.target.closest("[data-detail]");
  if (button) {
    showDetails(button.dataset.detail);
  }
});

  $("#detailClose").addEventListener("click", () => {
    detailDialog.close();
    resetHomeSeo();
  });

  detailDialog.addEventListener("close", () => {
    if (new URLSearchParams(window.location.search).has("job")) {
      resetHomeSeo();
    }
  });

  $("#searchBtn").addEventListener("click", () => {
    searchTerm = $("#searchInput").value.trim().toLowerCase();
    showAllJobs = false;
    renderJobs();
  });

  $("#searchInput").addEventListener("input", () => {
    searchTerm = $("#searchInput").value.trim().toLowerCase();
    showAllJobs = false;
    renderJobs();
  });

  const moreBtn = $("#showMoreJobs");

  if (moreBtn) {
    moreBtn.addEventListener("click", () => {
      showAllJobs = true;
      renderJobs();
    });
  }

  document.querySelectorAll(".cat").forEach(button => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".cat").forEach(item => {
        item.classList.remove("active");
      });

      button.classList.add("active");
      activeCategory = button.dataset.category;
      showAllJobs = false;
      renderJobs();
    });
  });

  $("#adminOpen").addEventListener("click", () => {
    adminDialog.showModal();
  });

  $("#adminClose").addEventListener("click", () => {
    adminDialog.close();
  });

  $("#loginForm").addEventListener("submit", async event => {
    event.preventDefault();

    const message = $("#loginMessage");
    message.textContent = "";

    if (!supabase) {
      message.textContent =
        "Pehle config.js mein Supabase URL aur anon key set karein.";
      return;
    }

    const email = $("#adminEmail").value.trim();
    const password = $("#adminPassword").value;

    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password
    });

    if (error) {
      message.textContent =
        "Login nahi hua. Email/password aur Supabase user check karein.";
      return;
    }

    currentUser = data.user;
    await renderAdmin();
  });

  async function renderAdmin(page = 0) {
    const pageSize = 30;
    const from = page * pageSize;
    const [listResult, totalResult, publishedResult, draftResult] = await Promise.all([
      supabase.from("jobs")
        .select("id,title,category,status,department,created_at", { count: "exact" })
        .order("created_at", { ascending: false })
        .range(from, from + pageSize - 1),
      supabase.from("jobs").select("id", { count: "exact", head: true }),
      supabase.from("jobs").select("id", { count: "exact", head: true }).eq("status", "published"),
      supabase.from("jobs").select("id", { count: "exact", head: true }).eq("status", "draft")
    ]);
    const { data, error } = listResult;

    if (error) {
      $("#adminRoot").innerHTML = `
        <h2>Dashboard load nahi hua</h2>
        <p>Database schema/RLS policy check karein.
        ${escapeHtml(error.message)}</p>`;
      return;
    }

    const jobs = data || [];
    const totalJobs = totalResult.count ?? listResult.count ?? jobs.length;
    const totalPages = Math.max(1, Math.ceil(totalJobs / pageSize));

    $("#adminRoot").innerHTML = `
      <div class="admin-panel-head">
        <div>
          <p class="eyebrow">SARKARI JOB ALERT • CONTENT CONTROL</p>
          <h2>Admin Control Center</h2>
          <p class="tiny-note">
            Logged in: ${escapeHtml(currentUser?.email || "Admin")}
          </p>
        </div>

        <div class="admin-actions">
          <button class="small-btn primary" id="newJob">+ Add Update</button>
          <button class="small-btn" id="logoutBtn">Logout</button>
        </div>
      </div>

      <div class="admin-stats">
        <div class="stat">
          <strong>${totalResult.count ?? totalJobs}</strong><span>Total posts</span>
        </div>
        <div class="stat">
          <strong>${publishedResult.count ?? 0}</strong>
          <span>Published</span>
        </div>
        <div class="stat">
          <strong>${draftResult.count ?? 0}</strong>
          <span>Drafts</span>
        </div>
      </div>

      <form id="jobForm" class="editor-form" hidden>
        <input type="hidden" id="jobId">

        <label>Post Title *
          <input id="jobTitle" required maxlength="180">
        </label>

        <label>Department / Board
          <input id="jobDepartment" maxlength="180">
        </label>

        <label>Category *
          <select id="jobCategory">
            <option value="Vacancy">Vacancy</option>
            <option value="Admit Card">Admit Card</option>
            <option value="Result">Result</option>
          </select>
        </label>

        <div id="vacancyFields" class="category-fields full">
          <div class="category-fields-title">Vacancy Details</div>

          <div class="category-fields-grid">
            <label>Vacancies / Update
              <input id="jobVacancies" maxlength="80">
            </label>

            <label>Notification Date
              <input id="jobNotificationDate" type="date">
            </label>

            <label>Last Date to Apply
              <input id="jobLastDate" type="date">
            </label>

            <label>DOB Eligibility — From
              <input id="jobDobFrom" type="date">
            </label>

            <label>DOB Eligibility — To
              <input id="jobDobTo" type="date">
            </label>

            <label>Qualification
              <input id="jobQualification" maxlength="180">
            </label>

            <label>Application Fees
              <input id="jobFees" maxlength="180">
            </label>

            <label>Age Limit
              <input id="jobAge" maxlength="180">
            </label>

            <label>Selection Process
              <input id="jobSelection" maxlength="180">
            </label>

            <label>Apply Online URL
              <input id="jobApply" type="url">
            </label>
          </div>
        </div>

        <div id="admitCardFields" class="category-fields full" hidden>
          <div class="category-fields-title">Admit Card Details</div>

          <div class="category-fields-grid">
            <label>Exam Date
              <input id="jobExamDate" type="date">
            </label>

            <label>Admit Card Release Date
              <input id="jobAdmitReleaseDate" type="date">
            </label>

            <label class="full">Download Admit Card URL
              <input id="jobAdmitUrl" type="url">
            </label>
          </div>
        </div>

        <div id="resultFields" class="category-fields full" hidden>
          <div class="category-fields-title">Result Details</div>

          <div class="category-fields-grid">
            <label>Result Declaration Date
              <input id="jobResultDate" type="date">
            </label>

            <label>Result Status
              <input id="jobResultStatus" maxlength="120"
                     placeholder="Declared / Soon / Scorecard available">
            </label>

            <label class="full">Result Check URL
              <input id="jobResultUrl" type="url">
            </label>

            <label>Cut-off Details
              <input id="jobCutoff" maxlength="500">
            </label>

            <label>Merit List URL
              <input id="jobMeritUrl" type="url">
            </label>
          </div>
        </div>

        <label class="full">Official Notification PDF / URL
          <input id="jobNotification" type="url">
        </label>

        <label class="full">Complete Details
          <textarea id="jobDescription" maxlength="10000" minlength="80" required placeholder="Verified vacancy / admit card / result details yahan likhein..."></textarea>
        </label>

        <label>Status
          <select id="jobStatus">
            <option value="draft">Draft (not public)</option>
            <option value="published">Published (public)</option>
          </select>
        </label>

        <div class="editor-actions full">
          <button class="small-btn primary" type="submit">Save Update</button>
          <button class="small-btn" type="button" id="cancelEdit">Cancel</button>
        </div>

        <p id="saveMessage" class="form-message full"></p>
      </form>

      <div class="admin-tools">
        <input id="adminSearch" type="search"
               placeholder="Search title / department...">

        <select id="adminFilter">
          <option value="all">All posts</option>
          <option value="draft">Drafts only</option>
          <option value="published">Published only</option>
        </select>
      </div>

      <div class="admin-table-wrap">
        <table class="admin-table" id="adminList">
          <thead><tr><th>Post / Department</th><th>Category</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>
          ${jobs.length ? jobs.map(j => `
            <tr class="admin-row" data-search="${escapeHtml((j.title + " " + (j.department || "")).toLowerCase())}" data-status="${escapeHtml(j.status)}">
              <td class="admin-post-cell"><strong>${escapeHtml(j.title)}</strong><small>${escapeHtml(j.department || "Department not added")}</small></td>
              <td><span class="admin-category">${escapeHtml(displayCategory(j.category))}</span></td>
              <td><span class="admin-status ${j.status === "published" ? "is-published" : "is-draft"}">${j.status === "published" ? "● Published" : "● Draft"}</span></td>
              <td><div class="admin-item-actions">
                <button class="small-btn" data-edit="${escapeHtml(j.id)}">Edit</button>
                <button class="small-btn" data-toggle="${escapeHtml(j.id)}" data-status="${escapeHtml(j.status)}">${j.status === "published" ? "Unpublish" : "Publish"}</button>
                <button class="small-btn danger-btn" data-delete="${escapeHtml(j.id)}">Delete</button>
              </div></td>
            </tr>`).join("") : '<tr><td colspan="4" class="admin-empty">Is page par koi post nahi hai.</td></tr>'}
          </tbody>
        </table>
      </div>
      <div class="admin-pagination">
        <span>Showing ${jobs.length ? from + 1 : 0}–${from + jobs.length} of ${totalJobs} posts</span>
        <div><button class="small-btn" id="adminPrev" ${page <= 0 ? "disabled" : ""}>← Previous</button>
        <b>Page ${page + 1} / ${totalPages}</b>
        <button class="small-btn" id="adminNext" ${page + 1 >= totalPages ? "disabled" : ""}>Next →</button></div>
      </div>
    `;

    $("#newJob").onclick = () => openEditor();

    $("#cancelEdit").onclick = () => {
      $("#jobForm").hidden = true;
      editingId = null;
    };

    $("#logoutBtn").onclick = async () => {
      await supabase.auth.signOut();
      currentUser = null;
      $("#adminRoot").innerHTML = loginMarkup();
    };

    $("#jobForm").onsubmit = saveJob;

    $("#jobCategory").addEventListener("change", updateCategoryFields);

    $("#adminRoot").querySelectorAll("[data-edit]").forEach(button => {
      button.onclick = async () => {
        button.disabled = true;
        button.textContent = "Loading…";
        const { data: fullJob, error: editError } = await supabase
          .from("jobs").select("*").eq("id", button.dataset.edit).single();
        button.disabled = false;
        button.textContent = "Edit";
        if (editError || !fullJob) { toast("Post load nahi hui: " + (editError?.message || "Not found")); return; }
        openEditor(fullJob);
      };
    });

    $("#adminRoot").querySelectorAll("[data-toggle]").forEach(button => {
      button.onclick = () => {
        changeStatus(
          button.dataset.toggle,
          button.dataset.status === "published" ? "draft" : "published"
        );
      };
    });

    $("#adminRoot").querySelectorAll("[data-delete]").forEach(button => {
      button.onclick = () => deleteJob(button.dataset.delete);
    });

    const filter = () => {
      const term = ($("#adminSearch").value || "").trim().toLowerCase();
      const state = $("#adminFilter").value || "all";

      $("#adminList").querySelectorAll(".admin-row").forEach(item => {
        item.hidden = !((!term || item.dataset.search.includes(term)) &&
          (state === "all" || item.dataset.status === state));
      });
    };

    $("#adminSearch").addEventListener("input", filter);
    $("#adminFilter").addEventListener("change", filter);
    $("#adminPrev").onclick = () => renderAdmin(page - 1);
    $("#adminNext").onclick = () => renderAdmin(page + 1);
  }

  function updateCategoryFields() {
    const category = $("#jobCategory")?.value || "Vacancy";

    $("#vacancyFields").hidden = category !== "Vacancy";
    $("#admitCardFields").hidden = category !== "Admit Card";
    $("#resultFields").hidden = category !== "Result";
  }

  function loginMarkup() {
    return `
      <div class="admin-login-head">
        <span class="brand-mark">SA</span>
        <h2>Admin Dashboard</h2>
        <p>Private access for site owner</p>
      </div>

      <form id="loginForm" class="admin-form">
        <label>Email
          <input id="adminEmail" type="email"
                 autocomplete="username" required>
        </label>

        <label>Password
          <input id="adminPassword" type="password"
                 autocomplete="current-password" required>
        </label>

        <button type="submit" class="primary-btn">Secure Login</button>
        <p id="loginMessage" class="form-message"></p>
      </form>

      <p class="tiny-note">Public sign-up yahan disabled hai.</p>
    `;
  }

  function openEditor(job = null) {
    editingId = job?.id || null;

    const form = $("#jobForm");
    form.hidden = false;

    const values = {
      jobId: job?.id || "",
      jobTitle: job?.title || "",
      jobDepartment: job?.department || "",
      jobCategory: displayCategory(job?.category || "Vacancy"),

      jobVacancies: job?.vacancies || "",
      jobNotificationDate: job?.notification_date || "",
      jobLastDate: job?.last_date || "",
      jobDobFrom: job?.dob_from || "",
      jobDobTo: job?.dob_to || "",
      jobQualification: job?.qualification || "",
      jobFees: job?.fees || "",
      jobAge: job?.age_limit || "",
      jobSelection: job?.selection_process || "",
      jobApply: job?.apply_url || "",

      jobExamDate: job?.exam_date || "",
      jobAdmitReleaseDate: job?.admit_card_release_date || "",
      jobAdmitUrl: job?.admit_card_url || "",

      jobResultDate: job?.result_date || "",
      jobResultStatus: job?.result_status || "",
      jobResultUrl: job?.result_url || "",
      jobCutoff: job?.cutoff_details || job?.cutoff || "",
      jobMeritUrl: job?.merit_list_url || "",

      jobNotification: job?.notification_url || "",
      jobDescription: job?.description || "",
      jobStatus: job?.status || "draft"
    };

    Object.entries(values).forEach(([id, value]) => {
      const element = $("#" + id);
      if (element) element.value = value;
    });

    updateCategoryFields();

    form.scrollIntoView({
      behavior: "smooth",
      block: "start"
    });
  }

  async function sendPublishNotification(jobId) {
    try {
      const cfg = window.SJA_CONFIG || {};
      if (!cfg.PUSH_WORKER_URL || cfg.PUSH_WORKER_URL.includes("REPLACE-WITH")) {
        toast("Push error: PUSH_WORKER_URL config missing");
        return;
      }
      const { data, error: sessionError } = await supabase.auth.getSession();
      const token = data?.session?.access_token;
      if (sessionError || !token) {
        toast("Push error: Admin login session nahi mila. Logout/login karke dobara try karein.");
        return;
      }
      const response = await fetch(cfg.PUSH_WORKER_URL.replace(/\/$/, "") + "/notify", {
        method: "POST",
        headers: { "content-type": "application/json", "authorization": "Bearer " + token },
        body: JSON.stringify({ jobId: String(jobId) })
      });
      const responseText = await response.text();
      let result = {};
      try {
        result = responseText ? JSON.parse(responseText) : {};
      } catch {
        result = { detail: responseText.slice(0, 700) };
      }

      if (!response.ok) {
        const reason = result.error || result.detail || result.message || "Worker error";
        const stage = result.stage ? " [" + result.stage + "]" : "";
        toast("Push failed (" + response.status + ")" + stage + ": " + reason);
        console.error("Push Worker error:", response.status, result);
        return;
      }
      if (result.sent > 0) {
        toast("Notification sent: " + result.sent + " device(s)");
      } else if (result.duplicate) {
        toast("Push skipped: is job ki notification pehle bheji ja chuki hai.");
      } else {
        toast("Push not sent: " + (result.message || "No subscribed devices"));
      }
      console.log("Push Worker result:", result);
    } catch (e) {
      console.warn("Push notification request failed:", e);
      toast("Push request failed: " + (e.message || "Network/CORS error"));
    }
  }

  async function saveJob(event) {
    event.preventDefault();

    const message = $("#saveMessage");
    message.textContent = "";

    const category = $("#jobCategory").value;
    const descriptionText = $("#jobDescription").value.trim();
    if (descriptionText.length < 80) {
      message.textContent = "Complete Details mein kam se kam 80 characters ki useful, post-specific description likhein.";
      $("#jobDescription").focus();
      return;
    }

    const data = {
      title: $("#jobTitle").value.trim(),
      department: $("#jobDepartment").value.trim() || "Not specified",
      category,

      vacancies:
        category === "Vacancy"
          ? ($("#jobVacancies").value.trim() || "Not specified")
          : "Not applicable",

      qualification:
        category === "Vacancy"
          ? ($("#jobQualification").value.trim() || "Not specified")
          : "Not applicable",

      notification_date:
        category === "Vacancy"
          ? ($("#jobNotificationDate").value || null)
          : null,

      last_date:
        category === "Vacancy"
          ? ($("#jobLastDate").value || null)
          : null,

      dob_from:
        category === "Vacancy"
          ? ($("#jobDobFrom").value || null)
          : null,

      dob_to:
        category === "Vacancy"
          ? ($("#jobDobTo").value || null)
          : null,

      fees:
        category === "Vacancy"
          ? ($("#jobFees").value.trim() || "See official notification")
          : "Not applicable",

      age_limit:
        category === "Vacancy"
          ? ($("#jobAge").value.trim() || "See official notification")
          : "Not applicable",

      selection_process:
        category === "Vacancy"
          ? ($("#jobSelection").value.trim() || "See official notification")
          : "Not applicable",

      apply_url:
        category === "Vacancy"
          ? ($("#jobApply").value.trim() || null)
          : null,

      exam_date:
        category === "Admit Card"
          ? ($("#jobExamDate").value || null)
          : null,

      admit_card_release_date:
        category === "Admit Card"
          ? ($("#jobAdmitReleaseDate").value || null)
          : null,

      admit_card_url:
        category === "Admit Card"
          ? ($("#jobAdmitUrl").value.trim() || null)
          : null,

      result_date:
        category === "Result"
          ? ($("#jobResultDate").value || null)
          : null,

      result_status:
        category === "Result"
          ? ($("#jobResultStatus").value.trim() || "See official notification")
          : null,

      result_url:
        category === "Result"
          ? ($("#jobResultUrl").value.trim() || null)
          : null,

      cutoff_details:
        category === "Result"
          ? ($("#jobCutoff").value.trim() || null)
          : null,

      merit_list_url:
        category === "Result"
          ? ($("#jobMeritUrl").value.trim() || null)
          : null,

      notification_url:
        $("#jobNotification").value.trim() || null,

      description:
        $("#jobDescription").value.trim(),

      status:
        $("#jobStatus").value,

      updated_at:
        new Date().toISOString()
    };

    let result;

    try {
      result = editingId
        ? await supabase
            .from("jobs")
            .update(data)
            .eq("id", editingId)
            .select("id")
            .maybeSingle()
        : await supabase
            .from("jobs")
            .insert({
              ...data,
              created_by: currentUser.id
            })
            .select("id")
            .single();
    } catch (error) {
      message.textContent =
        "Save failed: " + (error?.message || String(error));
      return;
    }

    if (result.error) {
      message.textContent =
        "Save failed: " + result.error.message +
        ". Database columns aur NOT NULL constraints check karein.";
      return;
    }

    if (editingId && !result.data) {
      message.textContent =
        "Update nahi hua. RLS policy ya record ID check karein.";
      return;
    }

    toast(editingId ? "Changes saved" : "New update saved");

    if (data.status === "published" && result.data?.id) {
      await sendPublishNotification(result.data.id);
    }

    await loadJobs();
    await renderAdmin();
  }

  async function changeStatus(id, status) {
    const { data, error } = await supabase
      .from("jobs")
      .update({
        status,
        updated_at: new Date().toISOString()
      })
      .eq("id", id)
      .select("id")
      .maybeSingle();

    if (error) {
      toast("Publish/Unpublish failed: " + error.message);
      return;
    }

    if (!data) {
      toast("Status nahi badla. RLS policy ya record ID check karein.");
      return;
    }

    toast(
      status === "published"
        ? "Post published"
        : "Post draft mein chali gayi"
    );

    if (status === "published") {
      await sendPublishNotification(data.id || id);
    }

    await loadJobs();
    await renderAdmin();
  }

  async function deleteJob(id) {
    if (!confirm("Kya aap is post ko permanently delete karna chahte hain?")) {
      return;
    }

    const { data, error } = await supabase
      .from("jobs")
      .delete()
      .eq("id", id)
      .select("id")
      .maybeSingle();

    if (error) {
      toast("Delete failed: " + error.message);
      return;
    }

    if (!data) {
      toast("Delete nahi hua. RLS policy ya record ID check karein.");
      return;
    }

    toast("Post deleted");

    await loadJobs();
    await renderAdmin();
  }

  loadJobs();
})();