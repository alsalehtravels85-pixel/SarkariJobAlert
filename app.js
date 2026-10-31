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

  const demoJobs = [
    {
      id: "demo-1",
      title: "Sample: Junior Assistant Recruitment",
      department: "Sample Department (Demo only)",
      category: "Vacancy",
      vacancies: "Demo",
      qualification: "As per official notice",
      last_date: null,
      status: "published",
      description: "Demo entry only. Yeh real vacancy nahi hai.",
      notification_url: "",
      apply_url: ""
    },
    {
      id: "demo-2",
      title: "Sample: Admit Card Update",
      department: "Sample Exam Board (Demo only)",
      category: "Admit Card",
      exam_date: null,
      admit_card_release_date: null,
      status: "published",
      description: "Demo entry only. Official admit card link verify karein.",
      notification_url: "",
      admit_card_url: ""
    },
    {
      id: "demo-3",
      title: "Sample: Examination Result",
      department: "Sample Recruitment Board (Demo only)",
      category: "Result",
      result_date: null,
      result_status: "Demo",
      status: "published",
      description: "Demo entry only. Official result details verify karein.",
      notification_url: "",
      result_url: "",
      cutoff_details: "",
      merit_list_url: ""
    }
  ];

  function toast(message) {
    const el = $("#toast");
    if (!el) return;

    el.textContent = message;
    el.classList.add("show");

    setTimeout(() => el.classList.remove("show"), 2600);
  }

  async function loadJobs() {
    if (!supabase) {
      if (notice) notice.hidden = false;
      allJobs = demoJobs;
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
          </div>
        </article>`;
    }).join("");
  }

  function showDetails(id) {
    const job = allJobs.find(
      item => String(item.id) === String(id)
    );

    if (!job) return;

    const category = displayCategory(job.category);
    const rows = [];

    function addRow(label, value) {
      if (value === null || value === undefined || value === "") return;

      rows.push(`
        <tr>
          <th>${escapeHtml(label)}</th>
          <td>${escapeHtml(value)}</td>
        </tr>
      `);
    }

    function addLink(label, url) {
      if (!url) return;

      rows.push(`
        <tr>
          <th>${escapeHtml(label)}</th>
          <td>
            <a href="${escapeHtml(url)}"
               target="_blank"
               rel="noopener noreferrer">
              ${escapeHtml(label)} ↗
            </a>
          </td>
        </tr>
      `);
    }

    if (category === "Vacancy") {
      addRow("Total Vacancies", job.vacancies);
      addRow("Qualification", job.qualification);
      addRow("Notification Date", formatDate(job.notification_date));
      addRow("Last Date to Apply", formatDate(job.last_date));

      if (job.dob_from || job.dob_to) {
        addRow(
          "DOB Eligibility",
          `${job.dob_from ? formatDate(job.dob_from) : "Any"} to ${
            job.dob_to ? formatDate(job.dob_to) : "Any"
          }`
        );
      }

      addRow("Application Fees", job.fees);
      addRow("Age Limit", job.age_limit);
      addRow("Selection Process", job.selection_process);

      addLink("Official Notification", job.notification_url);
      addLink("Apply Online", job.apply_url);
    }

    if (category === "Admit Card") {
      addRow("Exam Date", formatDate(job.exam_date));
      addRow(
        "Admit Card Release Date",
        formatDate(job.admit_card_release_date)
      );

      addLink("Download Admit Card", job.admit_card_url);
      addLink("Official Notification", job.notification_url);
    }

    if (category === "Result") {
      addRow("Result Date", formatDate(job.result_date));
      addRow(
        "Result Status",
        job.result_status || "See official notification"
      );

      addLink("Check Result", job.result_url);

      addRow(
        "Cut-off Details",
        job.cutoff_details || job.cutoff || ""
      );

      addLink("Merit List", job.merit_list_url);
      addLink("Official Notification", job.notification_url);
    }

    $("#detailContent").innerHTML = `
      <span class="tag">${escapeHtml(category)}</span>

      <h2 class="detail-title">${escapeHtml(job.title)}</h2>

      <p class="detail-dept">
        ${escapeHtml(job.department || "Department not specified")}
      </p>

      <table class="detail-table">
        <tbody>${rows.join("")}</tbody>
      </table>

      <h3>Complete Details</h3>

      <div class="detail-copy">
        ${escapeHtml(
          job.description ||
          "Please read the official notification carefully."
        )}
      </div>

      <p class="tiny-note">
        Dates aur links ko apply karne se pehle official website par verify karein.
      </p>
    `;

    detailDialog.showModal();
  }

  document.addEventListener("click", event => {
    const button = event.target.closest("[data-detail]");
    if (button) showDetails(button.dataset.detail);
  });

  $("#detailClose").addEventListener("click", () => {
    detailDialog.close();
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

  async function renderAdmin() {
    const { data, error } = await supabase
      .from("jobs")
      .select("*")
      .order("created_at", { ascending: false });

    if (error) {
      $("#adminRoot").innerHTML = `
        <h2>Dashboard load nahi hua</h2>
        <p>Database schema/RLS policy check karein.
        ${escapeHtml(error.message)}</p>`;
      return;
    }

    const jobs = data || [];

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
          <strong>${jobs.length}</strong><span>Total posts</span>
        </div>
        <div class="stat">
          <strong>${jobs.filter(j => j.status === "published").length}</strong>
          <span>Published</span>
        </div>
        <div class="stat">
          <strong>${jobs.filter(j => j.status === "draft").length}</strong>
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
          <textarea id="jobDescription" maxlength="10000"></textarea>
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

      <div class="admin-list" id="adminList">
        ${
          jobs.length
            ? jobs.map(j => `
              <div class="admin-item">
                <div>
                  <h4>${escapeHtml(j.title)}</h4>
                  <p>
                    ${escapeHtml(displayCategory(j.category))} •
                    ${escapeHtml(j.status)} •
                    ${escapeHtml(j.department || "No department")}
                  </p>
                </div>

                <div class="admin-item-actions">
                  <button class="small-btn" data-edit="${escapeHtml(j.id)}">
                    Edit
                  </button>

                  <button class="small-btn"
                          data-toggle="${escapeHtml(j.id)}"
                          data-status="${escapeHtml(j.status)}">
                    ${j.status === "published" ? "Unpublish" : "Publish"}
                  </button>

                  <button class="small-btn" data-delete="${escapeHtml(j.id)}">
                    Delete
                  </button>
                </div>
              </div>
            `).join("")
            : '<div class="empty-state">Abhi posts nahi hain.</div>'
        }
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
      button.onclick = () => {
        openEditor(
          jobs.find(j => String(j.id) === button.dataset.edit)
        );
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

      $("#adminList").querySelectorAll(".admin-item").forEach(item => {
        const text = item.textContent.toLowerCase();

        item.style.display =
          (!term || text.includes(term)) &&
          (state === "all" || text.includes("• " + state + " •"))
            ? ""
            : "none";
      });
    };

    $("#adminSearch").addEventListener("input", filter);
    $("#adminFilter").addEventListener("change", filter);
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

  async function saveJob(event) {
    event.preventDefault();

    const message = $("#saveMessage");
    message.textContent = "";

    const category = $("#jobCategory").value;

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
