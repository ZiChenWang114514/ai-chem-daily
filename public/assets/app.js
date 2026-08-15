const state = {
  payload: null,
  source: "all",
  query: "",
};

const groupOrder = ["今日精选", "方法与模型", "分子与药物发现", "结构与生物", "材料与催化"];

function formatDate(value) {
  if (!value) return "—";
  const parts = value.split("-");
  if (parts.length !== 3) return value;
  return `${parts[0]} 年 ${Number(parts[1])} 月 ${Number(parts[2])} 日`;
}

function formatGeneratedAt(value) {
  if (!value) return "生成时间暂缺";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return `生成于 ${new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date)}（北京时间）`;
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value ?? "—";
}

function paperSearchText(paper) {
  return [paper.title, paper.abstract, paper.author_line, paper.source, paper.category, ...(paper.tags || [])]
    .join(" ")
    .toLocaleLowerCase("zh-CN");
}

function visiblePapers() {
  if (!state.payload) return [];
  const query = state.query.trim().toLocaleLowerCase("zh-CN");
  return state.payload.papers.filter((paper) => {
    const sourceMatches = state.source === "all" || paper.source === state.source;
    const queryMatches = !query || paperSearchText(paper).includes(query);
    return sourceMatches && queryMatches;
  });
}

function createPaperCard(paper) {
  const template = document.getElementById("paper-template");
  const fragment = template.content.cloneNode(true);
  const article = fragment.querySelector("article");
  article.dataset.source = paper.source;
  fragment.querySelector(".rank").textContent = String(paper.rank).padStart(2, "0");
  fragment.querySelector(".source-badge").textContent = paper.source;
  fragment.querySelector(".topic-label").textContent = paper.featured ? "★ 今日精选" : paper.category;
  fragment.querySelector(".score-label").textContent = `综合评分 ${Math.round(paper.quality_score || 0)}`;
  const title = fragment.querySelector(".paper-title");
  title.href = paper.url;
  title.textContent = paper.title;
  fragment.querySelector(".paper-meta").textContent = `${paper.author_line || "作者信息暂缺"} · ${paper.published || "日期暂缺"}`;
  fragment.querySelector(".summary-zh").textContent = paper.summary_zh || "中文说明暂缺，请查看英文摘要。";
  fragment.querySelector(".why-it-matters").textContent = paper.why_it_matters_zh || "请结合原文判断研究价值。";
  fragment.querySelector(".abstract-text").textContent = paper.abstract || "该数据源未提供摘要。";
  const tagList = fragment.querySelector(".tag-list");
  [...new Set(paper.tags || [])].slice(0, 6).forEach((tag) => {
    const span = document.createElement("span");
    span.className = "tag";
    span.textContent = tag;
    tagList.appendChild(span);
  });
  return fragment;
}

function renderPapers() {
  const papers = visiblePapers();
  const container = document.getElementById("paper-groups");
  const empty = document.getElementById("empty-state");
  container.replaceChildren();
  empty.hidden = papers.length > 0;
  setText("result-count", `显示 ${papers.length} / ${state.payload?.papers?.length || 0} 篇`);

  const groups = new Map();
  papers.forEach((paper) => {
    const group = paper.featured ? "今日精选" : (paper.category || "方法与模型");
    if (!groups.has(group)) groups.set(group, []);
    groups.get(group).push(paper);
  });

  groupOrder.forEach((name) => {
    const items = groups.get(name);
    if (!items?.length) return;
    const section = document.createElement("section");
    section.className = "paper-group";
    const title = document.createElement("h3");
    title.className = "group-title";
    title.append(document.createTextNode(name));
    const count = document.createElement("span");
    count.textContent = `${items.length} 篇`;
    title.appendChild(count);
    section.appendChild(title);
    items.forEach((paper) => section.appendChild(createPaperCard(paper)));
    container.appendChild(section);
  });
}

function renderPayload(payload) {
  state.payload = payload;
  document.title = `${payload.title || "AI × Chem 每日预印本精选"} · ${payload.date || ""}`;
  setText("subtitle", payload.subtitle);
  setText("digest-date", formatDate(payload.date));
  document.getElementById("digest-date").dateTime = payload.date || "";
  setText("window-text", `覆盖 ${payload.window?.start || "—"} 至 ${payload.window?.end || "—"}`);
  setText("generated-time", formatGeneratedAt(payload.generated_at));
  setText("stat-fetched", payload.stats?.fetched?.toLocaleString("zh-CN") || 0);
  setText("stat-candidates", payload.stats?.candidates?.toLocaleString("zh-CN") || 0);
  setText("stat-selected", payload.stats?.selected?.toLocaleString("zh-CN") || 0);
  setText("method-label", payload.method);
  setText("footer-date", `最近更新：${payload.date || "—"}`);

  const note = document.getElementById("method-note");
  const messages = [payload.method_note];
  if (payload.source_errors?.length) {
    messages.push(`本期数据提示：${payload.source_errors.join("；")}`);
    note.classList.add("has-error");
  } else {
    note.classList.remove("has-error");
  }
  note.querySelector("p").textContent = messages.filter(Boolean).join(" ");
  renderPapers();
}

async function loadArchiveIndex() {
  const container = document.getElementById("history-list");
  try {
    const response = await fetch("data/archive/index.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const archive = await response.json();
    container.replaceChildren();
    (archive.items || []).forEach((item) => {
      const link = document.createElement("a");
      link.className = "history-link";
      link.href = item.kind === "html" ? item.href : `?date=${encodeURIComponent(item.date)}`;
      link.textContent = formatDate(item.date);
      const count = document.createElement("span");
      count.textContent = item.selected ? `${item.selected} 篇精选` : "历史版本";
      link.appendChild(count);
      container.appendChild(link);
    });
  } catch (error) {
    container.textContent = `历史列表读取失败：${error.message}`;
  }
}

async function loadDigest() {
  const params = new URLSearchParams(location.search);
  const requestedDate = params.get("date");
  const dataUrl = requestedDate ? `data/archive/${encodeURIComponent(requestedDate)}.json` : "data/latest.json";
  try {
    const response = await fetch(dataUrl, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    renderPayload(await response.json());
  } catch (error) {
    document.getElementById("paper-groups").innerHTML = `
      <div class="empty-state"><strong>日报数据暂时无法读取</strong><p>${error.message}</p></div>`;
    setText("digest-date", "读取失败");
  }
}

document.getElementById("search-input").addEventListener("input", (event) => {
  state.query = event.target.value;
  renderPapers();
});

document.getElementById("source-filters").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-source]");
  if (!button) return;
  state.source = button.dataset.source;
  document.querySelectorAll("button[data-source]").forEach((item) => item.classList.toggle("is-active", item === button));
  renderPapers();
});

const historyButton = document.getElementById("history-button");
const historyPanel = document.getElementById("history-panel");
historyButton.addEventListener("click", () => {
  const expanded = historyButton.getAttribute("aria-expanded") === "true";
  historyButton.setAttribute("aria-expanded", String(!expanded));
  historyPanel.hidden = expanded;
});

document.addEventListener("click", (event) => {
  if (historyPanel.hidden || historyPanel.contains(event.target) || historyButton.contains(event.target)) return;
  historyPanel.hidden = true;
  historyButton.setAttribute("aria-expanded", "false");
});

Promise.all([loadDigest(), loadArchiveIndex()]);
