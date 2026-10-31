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

  const displayCategory = value => {
    const category = String(value || "").trim();

    if (["Latest Jobs", "Vacancy", "Jobs"].includes(category)) {
      return "Vacancy";
    }

    if (["Results", "Answer Key"].includes(category)) {
      return "Result";
    }

    return category || "Vacancy";
  };

  $("#year").textContent = new Date().getFullYear();

  const escapeHtml = (value = "") =>
    String(value).replace(/[&<>"']/g, c => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    }[c]));

  const formatDate = value =>
    value
      ? new Date(
          value + (String(value).length === 10 ? "T00:00:00" : "")
        ).toLocaleDateString("en-IN", {
          day: "2-digit",
          month: "short",
          year: "numeric"
        })
      : "As per notification";

  const isExpired = job =>
    job.last_date &&
    new Date(job.last_date + "T23:59:59") < new Date();

  const isNewJob = job => {
    if (!job.created_at) return false;

    const created = new Date(job.created_at).getTime();

    return (
      Number.isFinite(created) &&
      Date.now() - created >= 0 &&
      Date.now() - created < 3 * 24 * 60 * 60 * 1000
    );
  };

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
      description: "Demo entry only. Real vacancy nahi hai.",
      notification_url: "",
      apply_url: ""
    },
    {
      id: "demo-2",
      title: "Sample: Admit Card Update",
      department: "Sample Exam Board (Demo only)",
      category: "Admit Card",
      vacancies: "Demo",
      qualification: "Registered candidates",
      last_date: null,
      status: "published",
      description: "Demo entry only. Official source verify karein.",
      notification_url: "",
      apply_url: ""
    },
    {
      id: "demo-3",
      title: "Sample: Examination Result",
      department: "Sample Recruitment Board (Demo only)",
      category: "Result",
      vacancies: "Demo",
      qualification: "Exam candidates",
      last_date: null,
      status: "published",
      description: "Demo entry only. Official source verify karein.",
      notification_url: "",
      apply_url: ""
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
          "Live database connect nahi hua. Supabase settings aur policies check karein.";
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
      const categoryMatches =
        activeCategory === "All" ||
        displayCategory(job.category) === activeCategory;

      const text = (
        `${job.title} ${job.department} ${job.qualification || ""}`
      ).toLowerCase();

      return categoryMatches && text.includes(searchTerm);
    });

    count.textContent =
      `${filtered.length} update${filtered.length === 1 ? "" : "s"}`;

    const heading = $("#listingHeading");

    if (heading) {
      heading.textContent =
        activeCategory === "All" ? "Latest Updates" : activeCategory;
    }

    const visibleJobs = showAllJobs
      ? filtered
      : filtered.slice(0, 8);

    const moreBtn = $("#showMoreJobs");

    if (moreBtn) {
      moreBtn.hidden = filtered.length <= 8 || showAllJobs;
      moreBtn.textContent =
        `Show More Jobs (${Math.max(0, filtered.length - 8)} aur)`;
    }

    if (!filtered.length) {
      grid.innerHTML = `
        <div class="empty-state">
          <strong>Abhi koi matching update nahi mila.</strong><br>
          <span>Search badal kar dekhein ya baad mein check karein.</span>
        </div>`;
      return;
    }

    grid.innerHTML = visibleJobs.map(job => `
      <article class="job-card">
        <div class="card-top">
          <span class="tag">${escapeHtml(displayCategory(job.category))}</span>
          <span class="status-tag">
            ${isExpired(job) ? "Date passed" : "Check details"}
          </span>
        </div>

        <h3>
          ${escapeHtml(job.title)}
          ${isNewJob(job) ? '<span class="new-badge">NEW</span>' : ""}
        </h3>

        <p class="department">
          ${escapeHtml(job.department || "Department not specified")}
        </p>

        <div class="card-meta">
          <div class="meta-item">
            <small>Vacancies / Update</small>
            <strong>${escapeHtml(job.vacancies || "See notice")}</strong>
          </div>

          <div class="meta-item">
            <small>Last date</small>
            <strong>${escapeHtml(formatDate(job.last_date))}</strong>
          </div>
        </div>

        <div class="card-actions">
          <button class="details-btn" data-detail="${escapeHtml(job.id)}">
            View Details
          </button>

          ${
            job.apply_url
              ? `<a class="apply-btn"
                    href="${escapeHtml(job.apply_url)}"
                    target="_blank"
                    rel="noopener noreferrer">Official Link ↗</a>`
              : `<button class="apply-btn" data-detail="${escapeHtml(job.id)}">
                   Read Update
                 </button>`
          }
        </div>
      </article>
    `).join("");
  }

  function showDetails(id) {
    const job = allJobs.find(
      item => String(item.id) === String(id)
    );

    if (!job) return;

    const category = displayCategory(job.category);

    let categoryDetails = "";

    if (category === "Admit Card") {
      categoryDetails = `
        <tr>
          <th>Exam Date</th>
          <td>${escapeHtml(formatDate(job.exam_date))}</td>
        </tr>
        <tr>
          <th>Admit Card Release Date</th>
          <td>${escapeHtml(formatDate(job.admit_card_release_date))}</td>
        </tr>
        ${
          job.admit_card_url
            ? `<tr><th>Admit Card</th><td>
                 <a href="${escapeHtml(job.admit_card_url)}"
                    target="_blank" rel="noopener noreferrer">
                   Download Admit Card ↗
                 </a>
               </td></tr>`
            : ""
        }
      `;
    }

    if (category === "Result") {
      categoryDetails = `
        <tr>
          <th>Result Date</th>
          <td>${escapeHtml(formatDate(job.result_date))}</td>
        </tr>
        <tr>
          <th>Result Status</th>
          <td>${escapeHtml(job.result_status || "See official notice")}</td>
        </tr>
        ${
          job.result_url
            ? `<tr><th>Result Link</th><td>
                 <a href="${escapeHtml(job.result_url)}"
                    target="_blank" rel="noopener noreferrer">
                   Check Result ↗
                 </a>
               </td></tr>`
            : ""
        }
        <tr>
          <th>Cut-off</th>
          <td>${escapeHtml(job.cutoff || "See official notice")}</td>
        </tr>
        ${
          job.merit_list_url
            ? `<tr><th>Merit List</th><td>
                 <a href="${escapeHtml(job.merit_list_url)}"
                    target="_blank" rel="noopener noreferrer">
                   View Merit List ↗
                 </a>
               </td></tr>`
            : ""
        }
      `;
    }

    $("#detailContent").innerHTML = `
      <span class="tag">${escapeHtml(category)}</span>

      <h2 class="detail-title">${escapeHtml(job.title)}</h2>

      <p class="detail-dept">
        ${escapeHtml(job.department || "Department not specified")}
      </p>

      <table class="detail-table">
        <tbody>
          ${
            category === "Vacancy"
              ? `
                <tr>
                  <th>Vacancies</th>
                  <td>${escapeHtml(job.vacancies || "See notification")}</td>
                </tr>
                <tr>
                  <th>Qualification</th>
                  <td>${escapeHtml(job.qualification || "See official notification")}</td>
                </tr>
                <tr>
                  <th>DOB Eligibility</th>
                  <td>${escapeHtml(
                    job.dob_from || job.dob_to
                      ? `${job.dob_from ? formatDate(job.dob_from) : "Any"} to ${job.dob_to ? formatDate(job.dob_to) : "Any"}`
                      : "See official notification"
                  )}</td>
                </tr>
                <tr>
                  <th>Fees</th>
                  <td>${escapeHtml(job.fees || "See official notification")}</td>
                </tr>
                <tr>
                  <th>Age Limit</th>
                  <td>${escapeHtml(job.age_limit || "See official notification")}</td>
                </tr>
                <tr>
                  <th>Selection</th>
                  <td>${escapeHtml(job.selection_process || "See official notification")}</td>
                </tr>
              `
              : ""
          }

          <tr>
            <th>Notification Date</th>
            <td>${escapeHtml(formatDate(job.notification_date))}</td>
          </tr>

          <tr>
            <th>Last Date</th>
            <td>${escapeHtml(formatDate(job.last_date))}</td>
          </tr>

          ${categoryDetails}
        </tbody>
      </table>

      <h3>Important Information</h3>

      <div class="detail-copy">
        ${escapeHtml(job.description || "Please read the official notification carefully.")}
      </div>

      <div class="card-actions">
        ${
          job.notification_url
            ? `<a class="details-btn"
                  href="${escapeHtml(job.notification_url)}"
                  target="_blank" rel="noopener noreferrer">
                 Official Notification ↗
               </a>`
            : ""
        }

        ${
          job.apply_url
            ? `<a class="apply-btn"
                  href="${escapeHtml(job.apply_url)}"
                  target="_blank" rel="noopener noreferrer">
                 Apply Online ↗
               </a>`
            : ""
        }
      </div>

      <p class="tiny-note">
        Apply karne se pehle official website par dates, eligibility aur links verify karein.
      </p>
    `;

    detailDialog.showModal();
  }

  document.addEventListener("click", event => {
    const detailButton = event.target.closest("[data-detail]");

    if (detailButton) {
      showDetails(detailButton.dataset.detail);
    }
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

  const showMoreJobsBtn = $("#showMoreJobs");

  if (showMoreJobsBtn) {
    showMoreJobsBtn.addEventListener("click", () => {
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
            Add updates and publish after verification.
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

        <label>Post title *
          <input id="jobTitle" required maxlength="180">
        </label>

        <label>Department
          <input id="jobDepartment" maxlength="180">
        </label>

        <label>Category *
          <select id="jobCategory">
            <option value="Vacancy">Vacancy</option>
            <option value="Admit Card">Admit Card</option>
            <option value="Result">Result</option>
          </select>
        </label>

        <div id="vacancyFields" class="full">
          <div class="editor-form">
            <label>Vacancies / Update
              <input id="jobVacancies" maxlength="80">
            </label>

            <label>Qualification
              <input id="jobQualification" maxlength="180">
            </label>

            <label>DOB Eligibility — From
              <input id="jobDobFrom" type="date">
            </label>

            <label>DOB Eligibility — To
              <input id="jobDobTo" type="date">
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
          </div>
        </div>

        <div id="admitCardFields" class="full" hidden>
          <div class="editor-form">
            <label>Exam Date
              <input id="jobExamDate" type="date">
            </label>

            <label>Admit Card Release Date
              <input id="jobAdmitReleaseDate" type="date">
            </label>

            <label class="full">Admit Card URL
              <input id="jobAdmitUrl" type="url"
                     placeholder="Official admit card link">
            </label>
          </div>
        </div>

        <div id="resultFields" class="full" hidden>
          <div class="editor-form">
            <label>Result Date
              <input id="jobResultDate" type="date">
            </label>

            <label>Result Status
              <input id="jobResultStatus" maxlength="180"
                     placeholder="Declared / Pending">
            </label>

            <label>Cut-off
              <input id="jobCutoff" maxlength="500">
            </label>

            <label>Result URL
              <input id="jobResultUrl" type="url"
                     placeholder="Official result link">
            </label>

            <label class="full">Merit List URL
              <input id="jobMeritUrl" type="url"
                     placeholder="Official merit list link">
            </label>
          </div>
        </div>

        <label>Notification Date
          <input id="jobNotificationDate" type="date">
        </label>

        <label>Last Date
          <input id="jobLastDate" type="date">
        </label>

        <label>Official Notification URL
          <input id="jobNotification" type="url">
        </label>

        <label>Apply Online URL
          <input id="jobApply" type="url">
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
            ? jobs.map(job => `
              <div class="admin-item">
                <div>
                  <h4>${escapeHtml(job.title)}</h4>
                  <p>
                    ${escapeHtml(displayCategory(job.category))} •
                    ${escapeHtml(job.status)} •
                    ${escapeHtml(job.department || "No department")}
                  </p>
                </div>

                <div class="admin-item-actions">
                  <button class="small-btn" data-edit="${escapeHtml(job.id)}">Edit</button>
                  <button class="small-btn"
                          data-toggle="${escapeHtml(job.id)}"
                          data-status="${escapeHtml(job.status)}">
                    ${job.status === "published" ? "Unpublish" : "Publish"}
                  </button>
                  <button class="small-btn" data-delete="${escapeHtml(job.id)}">Delete</button>
                </div>
              </div>
            `).join("")
            : '<div class="empty-state">Abhi posts nahi hain. Add Update se pehli post banayein.</div>'
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
          jobs.find(job => String(job.id) === button.dataset.edit)
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

    const filterAdminList = () => {
      const term = ($("#adminSearch").value || "").trim().toLowerCase();
      const state = $("#adminFilter").value || "all";

      $("#adminList").querySelectorAll(".admin-item").forEach(item => {
        const text = item.textContent.toLowerCase();
        const matchesText = !term || text.includes(term);
        const matchesState = state === "all" || text.includes("• " + state + " •");

        item.style.display = matchesText && matchesState ? "" : "none";
      });
    };

    $("#adminSearch").addEventListener("input", filterAdminList);
    $("#adminFilter").addEventListener("change", filterAdminList);
  }

  function updateCategoryFields() {
    const category = $("#jobCategory").value;

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
          <input id="adminEmail" type="email" autocomplete="username" required>
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
      jobQualification: job?.qualification || "",
      jobDobFrom: job?.dob_from || "",
      jobDobTo: job?.dob_to || "",
      jobFees: job?.fees || "",
      jobAge: job?.age_limit || "",
      jobSelection: job?.selection_process || "",
      jobExamDate: job?.exam_date || "",
      jobAdmitReleaseDate: job?.admit_card_release_date || "",
      jobAdmitUrl: job?.admit_card_url || "",
      jobResultDate: job?.result_date || "",
      jobResultStatus: job?.result_status || "",
      jobResultUrl: job?.result_url || "",
      jobCutoff: job?.cutoff || "",
      jobMeritUrl: job?.merit_list_url || "",
      jobNotificationDate: job?.notification_date || "",
      jobLastDate: job?.last_date || "",
      jobNotification: job?.notification_url || "",
      jobApply: job?.apply_url || "",
      jobDescription: job?.description || "",
      jobStatus: job?.status || "draft"
    };

    Object.entries(values).forEach(([id, value]) => {
      const element = $("#" + id);
      if (element) element.value = value;
    });

    updateCategoryFields();
    form.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function saveJob(event) {
    event.preventDefault();

    const message = $("#saveMessage");
    message.textContent = "";

    const category = $("#jobCategory").value;

    /*
     * Important:
     * Existing database columns vacancies and qualification
     * may be NOT NULL. Always send a non-empty value.
     */
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

      dob_from: category === "Vacancy"
        ? ($("#jobDobFrom").value || null)
        : null,

      dob_to: category === "Vacancy"
        ? ($("#jobDobTo").value || null)
        : null,

      fees: category === "Vacancy"
        ? ($("#jobFees").value.trim() || "See official notification")
        : "Not applicable",

      age_limit: category === "Vacancy"
        ? ($("#jobAge").value.trim() || "See official notification")
        : "Not applicable",

      selection_process: category === "Vacancy"
        ? ($("#jobSelection").value.trim() || "See official notification")
        : "Not applicable",

      exam_date: category === "Admit Card"
        ? ($("#jobExamDate").value || null)
        : null,

      admit_card_release_date: category === "Admit Card"
        ? ($("#jobAdmitReleaseDate").value || null)
        : null,

      admit_card_url: category === "Admit Card"
        ? ($("#jobAdmitUrl").value.trim() || null)
        : null,

      result_date: category === "Result"
        ? ($("#jobResultDate").value || null)
        : null,

      result_status: category === "Result"
        ? ($("#jobResultStatus").value.trim() || "See official notification")
        : null,

      result_url: category === "Result"
        ? ($("#jobResultUrl").value.trim() || null)
        : null,

      cutoff: category === "Result"
        ? ($("#jobCutoff").value.trim() || null)
        : null,

      merit_list_url: category === "Result"
        ? ($("#jobMeritUrl").value.trim() || null)
        : null,

      notification_date: $("#jobNotificationDate").value || null,
      last_date: $("#jobLastDate").value || null,

      notification_url: $("#jobNotification").value.trim() || null,
      apply_url: $("#jobApply").value.trim() || null,

      description: $("#jobDescription").value.trim(),
      status: $("#jobStatus").value,
      updated_at: new Date().toISOString()
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
        ". Agar column missing ho, pehle Supabase migration run karein.";
      return;
    }

    if (editingId && !result.data) {
      message.textContent =
        "Record update nahi hua. Database permissions aur record ID check karein.";
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

    toast(status === "published" ? "Post published" : "Post draft mein chali gayi");

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
