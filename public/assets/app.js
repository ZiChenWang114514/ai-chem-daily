const page = document.body.dataset.page || "home";
const channelId = document.body.dataset.channel || "";
const root = document.body.dataset.root || "";
const state = { payload: null, manifest: null, archive: [], activity: [], activityMetric: "selected", source: "all", query: "" };
const channelNames = { aixchem: "AI × Chem", aixbio: "AI × Bio", aixmath: "AI × Math", aivoices: "AI Voices", engineering: "Engineering" };

function path(value) { return `${root}${value}`; }
function setText(id, value) { const element = document.getElementById(id); if (element) element.textContent = value ?? "—"; }
function formatDate(value) { if (!value) return "—"; const [y, m, d] = value.split("-"); return `${y} 年 ${Number(m)} 月 ${Number(d)} 日`; }
function formatGeneratedAt(value) {
  const date = new Date(value);
  if (!value || Number.isNaN(date.valueOf())) return "生成时间暂缺";
  return `生成于 ${new Intl.DateTimeFormat("zh-CN", { timeZone: "Asia/Shanghai", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false }).format(date)}（北京时间）`;
}
function dateKey(date) { return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}-${String(date.getUTCDate()).padStart(2, "0")}`; }
function dateFromKey(value) { const [y, m, d] = value.split("-").map(Number); return new Date(Date.UTC(y, m - 1, d)); }
function activityLevel(value, maximum) { if (!value || !maximum) return 0; return Math.max(1, Math.min(4, Math.ceil(Math.sqrt(value / maximum) * 4))); }

function renderHeatmap() {
  const container = document.getElementById("activity-heatmap");
  container.replaceChildren();
  const relevant = state.activity.filter((item) => page === "home" || item.channel === channelId);
  const byDate = new Map();
  relevant.forEach((item) => {
    const existing = byDate.get(item.date) || { date: item.date, fetched: 0, candidates: 0, selected: 0, href: item.href };
    ["fetched", "candidates", "selected"].forEach((metric) => { existing[metric] += Number(item[metric]) || 0; });
    if (!existing.href) existing.href = item.href;
    byDate.set(item.date, existing);
  });
  const metric = state.activityMetric;
  const maximum = Math.max(0, ...[...byDate.values()].map((item) => item[metric] || 0));
  const latestDate = [...byDate.keys()].sort().at(-1) || state.payload?.date || dateKey(new Date());
  const end = dateFromKey(latestDate); end.setUTCDate(end.getUTCDate() + (6 - end.getUTCDay()));
  const start = new Date(end); start.setUTCDate(start.getUTCDate() - 370);
  let previousMonth = -1; let populatedDays = 0; let total = 0;
  for (let offset = 0; offset < 371; offset += 1) {
    const day = new Date(start); day.setUTCDate(start.getUTCDate() + offset);
    const key = dateKey(day); const item = byDate.get(key); const value = Number(item?.[metric]) || 0;
    const week = Math.floor(offset / 7);
    if (day.getUTCMonth() !== previousMonth && (offset === 0 || day.getUTCDate() <= 7)) {
      previousMonth = day.getUTCMonth(); const month = document.createElement("span"); month.className = "heatmap__month"; month.style.setProperty("--week", week); month.textContent = `${day.getUTCMonth() + 1}月`; container.appendChild(month);
    }
    const cell = document.createElement(item?.href ? "button" : "span"); cell.className = "heatmap__day"; cell.dataset.level = activityLevel(value, maximum); cell.setAttribute("role", "gridcell");
    const label = `${formatDate(key)}：${metric === "selected" ? "精选" : metric === "candidates" ? "候选" : "采集"} ${value}`; cell.title = label; cell.setAttribute("aria-label", label);
    if (item?.href) { cell.type = "button"; cell.addEventListener("click", () => { location.href = page === "channel" ? `?date=${encodeURIComponent(key)}` : path(item.href); }); }
    container.appendChild(cell); if (value > 0) populatedDays += 1; total += value;
  }
  setText("activity-summary", `过去一年有 ${populatedDays} 天记录，共计 ${total.toLocaleString("zh-CN")} 条${metric === "selected" ? "精选" : metric === "candidates" ? "候选" : "采集记录"}`);
}

function renderChannels() {
  const container = document.getElementById("channel-cards");
  if (!state.manifest) return;
  container.replaceChildren();
  state.manifest.channels.forEach((channel) => {
    const card = document.createElement("a"); card.className = "channel-card is-active"; card.href = path(`channels/${channel.id}/`); card.style.setProperty("--channel-accent", channel.accent || "#0d7c78");
    const top = document.createElement("div"); top.className = "channel-card__top"; const title = document.createElement("h3"); title.textContent = channel.name; const status = document.createElement("span"); status.className = "channel-card__status"; status.textContent = "每日更新"; top.append(title, status);
    const description = document.createElement("p"); description.textContent = channel.description; const meta = document.createElement("span"); meta.className = "channel-card__meta"; meta.textContent = `最近一期 ${channel.latest_date || "等待生成"}`;
    card.append(top, description, meta); container.appendChild(card);
  });
}

function paperSearchText(item) { return [item.title, item.abstract_or_text, item.abstract, item.author_line, ...(item.creators || []), item.source, item.category, ...(item.tags || [])].join(" ").toLocaleLowerCase("zh-CN"); }
function visibleItems() { const query = state.query.trim().toLocaleLowerCase("zh-CN"); return (state.payload?.items || state.payload?.papers || []).filter((item) => (state.source === "all" || item.source === state.source) && (!query || paperSearchText(item).includes(query))); }

function createItemCard(item) {
  const fragment = document.getElementById("paper-template").content.cloneNode(true);
  fragment.querySelector(".rank").textContent = String(item.rank || 0).padStart(2, "0"); fragment.querySelector(".source-badge").textContent = item.source;
  fragment.querySelector(".topic-label").textContent = item.featured ? "★ 今日精选" : item.category; fragment.querySelector(".score-label").textContent = `综合评分 ${Math.round(item.quality_score || 0)}`;
  const title = fragment.querySelector(".paper-title"); title.href = item.url; title.textContent = item.title;
  const creators = item.author_line || (item.creators || []).slice(0, 3).join(", ") || "作者信息暂缺"; fragment.querySelector(".paper-meta").textContent = `${creators} · ${(item.published_at || item.published || "日期暂缺").slice(0, 10)}`;
  fragment.querySelector(".summary-zh").textContent = item.summary_zh || "中文说明暂缺，请查看原始内容。"; fragment.querySelector(".why-it-matters").textContent = item.why_it_matters_zh || "请结合原始来源判断其价值。";
  fragment.querySelector(".abstract-text").textContent = item.abstract_or_text || item.abstract || "该来源未提供摘要或正文。";
  const tags = fragment.querySelector(".tag-list"); [...new Set(item.tags || [])].slice(0, 6).forEach((tag) => { const span = document.createElement("span"); span.className = "tag"; span.textContent = tag; tags.appendChild(span); }); return fragment;
}

function renderItems() {
  const items = visibleItems(); const container = document.getElementById("paper-groups"); const empty = document.getElementById("empty-state"); container.replaceChildren(); empty.hidden = items.length > 0; setText("result-count", `显示 ${items.length} / ${(state.payload?.items || state.payload?.papers || []).length} 项`);
  const groups = new Map(); items.forEach((item) => { const group = item.featured ? "今日精选" : item.category || "其他更新"; if (!groups.has(group)) groups.set(group, []); groups.get(group).push(item); });
  ["今日精选", ...groups.keys()].filter((value, index, values) => values.indexOf(value) === index).forEach((name) => { const values = groups.get(name); if (!values?.length) return; const section = document.createElement("section"); section.className = "paper-group"; const title = document.createElement("h3"); title.className = "group-title"; title.append(document.createTextNode(name)); const count = document.createElement("span"); count.textContent = `${values.length} 项`; title.appendChild(count); section.appendChild(title); values.forEach((item) => section.appendChild(createItemCard(item))); container.appendChild(section); });
}

function renderSourceFilters() {
  const container = document.getElementById("source-filters"); container.replaceChildren(); const sources = ["all", ...new Set((state.payload?.items || state.payload?.papers || []).map((item) => item.source))]; sources.forEach((source) => { const button = document.createElement("button"); button.className = `filter-chip${source === "all" ? " is-active" : ""}`; button.type = "button"; button.dataset.source = source; button.textContent = source === "all" ? "全部来源" : source; container.appendChild(button); });
}

function renderPayload(payload) {
  state.payload = payload; const isHome = page === "home"; document.title = `${payload.title || channelNames[channelId] || "AIX Daily"} · ${payload.date || ""}`;
  if (!isHome) { setText("eyebrow", `${channelNames[channelId].toUpperCase()} · DAILY CURATION`); document.getElementById("hero-title").innerHTML = `${channelNames[channelId]}<br>每日研究精选`; }
  setText("subtitle", payload.subtitle || payload.overview_zh); setText("digest-date", formatDate(payload.date)); document.getElementById("digest-date").dateTime = payload.date || "";
  setText("window-text", isHome ? "五频道综合日报" : `覆盖 ${payload.window?.start || "—"} 至 ${payload.window?.end || "—"}`); setText("generated-time", formatGeneratedAt(payload.generated_at));
  const stats = isHome ? payload.channels.reduce((acc, channel) => ({ fetched: acc.fetched + (channel.stats.fetched || 0), candidates: acc.candidates + (channel.stats.candidates || 0), selected: acc.selected + (channel.stats.selected || 0) }), { fetched: 0, candidates: 0, selected: 0 }) : payload.stats;
  setText("stat-fetched", stats.fetched.toLocaleString("zh-CN")); setText("stat-candidates", stats.candidates.toLocaleString("zh-CN")); setText("stat-selected", stats.selected.toLocaleString("zh-CN")); setText("method-label", isHome ? "五频道串行审阅" : payload.method); setText("footer-date", `最近更新：${payload.date}`);
  const note = document.getElementById("method-note"); const errors = isHome ? payload.channels.flatMap((channel) => channel.source_errors || []) : payload.source_errors || []; note.querySelector("p").textContent = [isHome ? payload.overview_zh : payload.method_note, errors.length ? `数据提示：${errors.join("；")}` : ""].filter(Boolean).join(" "); note.classList.toggle("has-error", errors.length > 0);
  const sourceRow = document.getElementById("source-row"); sourceRow.replaceChildren(); [...new Set((state.payload.items || []).map((item) => item.source))].slice(0, 7).forEach((source) => { const span = document.createElement("span"); span.textContent = source; sourceRow.appendChild(span); });
  renderSourceFilters(); renderItems();
}

async function loadManifestAndActivity() {
  const [manifestResponse, activityResponse] = await Promise.all([fetch(path("api/v1/manifest.json"), { cache: "no-store" }), fetch(path("api/v1/activity.json"), { cache: "no-store" })]);
  if (!manifestResponse.ok || !activityResponse.ok) throw new Error("公共接口暂时不可用"); state.manifest = await manifestResponse.json(); state.activity = (await activityResponse.json()).items || []; renderChannels(); renderHeatmap();
  document.querySelectorAll(".channel-nav__item").forEach((link) => { const active = page === "channel" && link.getAttribute("href")?.includes(channelId); link.classList.toggle("is-active", active || (page === "home" && link.textContent.trim() === "总览")); if (active) link.setAttribute("aria-current", "page"); });
}

async function loadArchive() {
  const container = document.getElementById("history-list"); const archivePath = page === "channel" ? `data/channels/${channelId}/archive/index.json` : "api/v1/activity.json";
  try { const response = await fetch(path(archivePath), { cache: "no-store" }); const value = await response.json(); const items = page === "channel" ? value.items || [] : [...new Map((value.items || []).map((item) => [item.date, item])).values()].sort((a, b) => b.date.localeCompare(a.date)); container.replaceChildren(); items.forEach((item) => { const link = document.createElement("a"); link.className = "history-link"; link.href = page === "channel" ? `?date=${encodeURIComponent(item.date)}` : path(item.href || ""); link.textContent = formatDate(item.date); const count = document.createElement("span"); count.textContent = `${item.selected || 0} 项精选`; link.appendChild(count); container.appendChild(link); }); } catch (error) { container.textContent = `历史列表读取失败：${error.message}`; }
}

async function loadDigest() {
  const requestedDate = new URLSearchParams(location.search).get("date"); let url;
  if (page === "home") url = "data/daily/latest.json"; else url = requestedDate ? `data/channels/${channelId}/archive/${encodeURIComponent(requestedDate)}.json` : `data/channels/${channelId}/latest.json`;
  const response = await fetch(path(url), { cache: "no-store" }); if (!response.ok) throw new Error(`HTTP ${response.status}`); const payload = await response.json();
  if (page === "home") { payload.items = payload.channels.flatMap((channel) => channel.items.map((item, index) => ({ ...item, rank: index + 1, category: channel.name, featured: index === 0 }))); }
  renderPayload(payload);
}

document.getElementById("search-input").addEventListener("input", (event) => { state.query = event.target.value; renderItems(); });
document.getElementById("source-filters").addEventListener("click", (event) => { const button = event.target.closest("button[data-source]"); if (!button) return; state.source = button.dataset.source; document.querySelectorAll("button[data-source]").forEach((item) => item.classList.toggle("is-active", item === button)); renderItems(); });
document.getElementById("activity-tabs").addEventListener("click", (event) => { const button = event.target.closest("button[data-metric]"); if (!button) return; state.activityMetric = button.dataset.metric; document.querySelectorAll("#activity-tabs button").forEach((item) => item.classList.toggle("is-active", item === button)); renderHeatmap(); });
const historyButton = document.getElementById("history-button"); const historyPanel = document.getElementById("history-panel"); historyButton.addEventListener("click", () => { const open = historyButton.getAttribute("aria-expanded") === "true"; historyButton.setAttribute("aria-expanded", String(!open)); historyPanel.hidden = open; });

Promise.all([loadManifestAndActivity(), loadArchive(), loadDigest()]).catch((error) => { document.getElementById("paper-groups").innerHTML = `<div class="empty-state"><strong>日报数据暂时无法读取</strong><p>${error.message}</p></div>`; });
