const page = document.body.dataset.page || "home";
const channelId = document.body.dataset.channel || "";
const root = document.body.dataset.root || "";
const state = {
  payload: null,
  manifest: null,
  activity: [],
  archiveDates: new Set(),
  activityMetric: "selected",
  source: "all",
  query: "",
  heatmapSignature: "",
  searchIndex: new WeakMap(),
  libraryChannel: "all",
  libraryTag: "all",
  libraryQuery: "",
  noteTimers: {},
  toastTimer: 0,
  undoSnapshot: null,
  fetchCache: new Map(),
  abstractsPromise: null,
  activityScheduled: false,
};
const SITE_NAME = "AIxDaily";
const HUB_SOURCES = [
  "arXiv",
  "bioRxiv",
  "ChemRxiv",
  "medRxiv",
  "Europe PMC",
  "OpenReview",
  "X",
  "研究博客",
  "GitHub Releases",
  "官方更新日志",
];
const COLLECTION_KEY = AixCollection.KEY;
const UNTAGGED_LABEL = AixCollection.UNTAGGED;
const channelNames = {
  aixchem: "AI × Chem",
  aixbio: "AI × Bio",
  aixmath: "AI × Math",
  aivoices: "AI Voices",
  engineering: "Engineering",
};
const channelTitles = {
  aixchem: "化学",
  aixbio: "生命科学",
  aixmath: "数学",
  aivoices: "公开观点",
  engineering: "工程更新",
};
const weekdays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];
const generatedFormat = new Intl.DateTimeFormat("zh-CN", {
  timeZone: "Asia/Shanghai",
  month: "numeric",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

function path(value) {
  return `${root}${value}`;
}

async function loadJSON(url, options = {}) {
  const href = path(url);
  if (!options.fresh && state.fetchCache.has(href)) return state.fetchCache.get(href);
  const init = {};
  if (options.priority) init.priority = options.priority;
  const pending = fetch(href, init).then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }).catch((error) => {
    state.fetchCache.delete(href);
    throw error;
  });
  state.fetchCache.set(href, pending);
  return pending;
}

function requestedDate() {
  return new URLSearchParams(location.search).get("date") || "";
}

function viewingHistory() {
  return Boolean(requestedDate());
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value ?? "—";
}

function formatDate(value) {
  if (!value) return "—";
  const [year, month, day] = value.split("-");
  return `${year} 年 ${Number(month)} 月 ${Number(day)} 日`;
}

function weekdayLabel(value) {
  if (!value) return "";
  const [year, month, day] = value.split("-").map(Number);
  return weekdays[new Date(year, month - 1, day).getDay()] || "";
}

function formatGeneratedAt(value) {
  const date = new Date(value);
  if (!value || Number.isNaN(date.valueOf())) return "生成时间暂缺";
  const parts = generatedFormat.formatToParts(date);
  const read = (type) => parts.find((part) => part.type === type)?.value || "";
  return `${read("month")} 月 ${read("day")} 日 ${read("hour")}:${read("minute")} 更新`;
}

function dateKey(date) {
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}-${String(date.getUTCDate()).padStart(2, "0")}`;
}

function dateFromKey(value) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

function withDate(href, date) {
  if (!date) return href;
  const glue = href.includes("?") ? "&" : "?";
  return `${href}${glue}date=${encodeURIComponent(date)}`;
}

function activityLevel(value, maximum) {
  if (!value || !maximum) return 0;
  return Math.max(1, Math.min(4, Math.ceil(Math.sqrt(value / maximum) * 4)));
}

function payloadItems(payload = state.payload) {
  return payload?.items || payload?.papers || [];
}

function currentDate() {
  return requestedDate() || state.payload?.date || "";
}

function friendlySourceNote(errors) {
  const names = [...new Set((errors || []).map((item) => String(item).split(":")[0].trim()).filter(Boolean))];
  if (!names.length) return "";
  return `部分来源今日暂不可用：${names.join("、")}`;
}

function displayTitle(item) {
  const title = (item.title || "").trim();
  const repo = item.metadata?.repository || "";
  const version = item.metadata?.version || "";
  if (repo && version && (!title || /^b\d+$/i.test(title) || title === version)) {
    return `${repo.split("/").pop()} ${version}`;
  }
  return title || "未命名条目";
}
window.displayTitle = displayTitle;

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatMarkupHtml(text) {
  return escapeHtml(text)
    .replace(/\$([^$]{1,80})\$/g, "$1")
    .replace(/\^\{([^{}]{1,40})\}/g, "<sup>$1</sup>")
    .replace(/_\{([^{}]{1,40})\}/g, "<sub>$1</sub>")
    .replace(/\^([+\-]?\d+)/g, "<sup>$1</sup>")
    .replace(/\^([A-Za-z])/g, "<sup>$1</sup>")
    .replace(/_([+\-]?\d+)/g, "<sub>$1</sub>");
}

function setRichText(node, text) {
  if (!node) return;
  const holder = document.createElement("span");
  holder.innerHTML = formatMarkupHtml(text ?? "");
  node.replaceChildren(...holder.childNodes);
}

function sameText(left, right) {
  return String(left || "").replace(/\s+/g, "") === String(right || "").replace(/\s+/g, "");
}

function collectionItemKey(item) {
  return AixCollection.key(item);
}

function itemAnchor(item) {
  return `item-${collectionItemKey(item).replace(/[^A-Za-z0-9]+/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "")}`;
}

function itemPermalink(item) {
  const url = new URL(location.href);
  url.hash = itemAnchor(item);
  return url.toString();
}

async function copyItemLink(item) {
  const text = itemPermalink(item);
  try {
    await navigator.clipboard.writeText(text);
    showToast("已复制本页链接");
    return;
  } catch {
    /* fall through to a selection-based copy */
  }
  const field = document.createElement("textarea");
  field.value = text;
  field.setAttribute("readonly", "");
  field.style.position = "fixed";
  field.style.left = "-9999px";
  document.body.appendChild(field);
  field.select();
  const ok = document.execCommand("copy");
  field.remove();
  showToast(ok ? "已复制本页链接" : "复制失败，请手动复制地址栏");
}

function focusItemFromHash() {
  const id = decodeURIComponent((location.hash || "").replace(/^#/, ""));
  if (!id) return false;
  const card = document.getElementById(id);
  if (!card) return false;
  document.querySelectorAll(".paper-card.is-target").forEach((node) => node.classList.remove("is-target"));
  card.classList.add("is-target");
  card.scrollIntoView({ block: "start", behavior: "smooth" });
  return true;
}

function savedRecord(item) {
  return AixCollection.record(item);
}

function recordTags(record) {
  return AixCollection.tagsOf(record);
}

function collectionRecords() {
  return AixCollection.records();
}

function tagCounts(records) {
  const counts = new Map();
  records.forEach((record) => {
    const tags = recordTags(record);
    if (!tags.length) {
      counts.set(UNTAGGED_LABEL, (counts.get(UNTAGGED_LABEL) || 0) + 1);
      return;
    }
    tags.forEach((tag) => counts.set(tag, (counts.get(tag) || 0) + 1));
  });
  return [...counts.entries()].sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0], "zh-CN"));
}

function showToast(message, action) {
  let toast = document.getElementById("site-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "site-toast";
    toast.className = "site-toast";
    toast.setAttribute("role", "status");
    toast.setAttribute("aria-live", "polite");
    toast.setAttribute("aria-atomic", "true");
    document.body.appendChild(toast);
  }
  toast.replaceChildren();
  const text = document.createElement("span");
  text.textContent = message;
  toast.appendChild(text);
  if (action?.label && action.onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = action.label;
    button.addEventListener("click", () => {
      action.onClick();
      toast.hidden = true;
    });
    toast.appendChild(button);
  }
  toast.hidden = false;
  window.clearTimeout(state.toastTimer);
  state.toastTimer = window.setTimeout(() => {
    toast.hidden = true;
    state.undoSnapshot = null;
  }, 5000);
}

function toggleSaved(item) {
  const current = savedRecord(item);
  if (current) {
    const removed = AixCollection.remove(item);
    if (!removed) {
      showToast("本机存储写入失败，收藏未更新");
      return true;
    }
    state.undoSnapshot = removed;
    showToast(removed.note ? "已取消收藏，笔记仍留在本机。" : "已取消收藏。", {
      label: "撤销",
      onClick: () => {
        AixCollection.restore(state.undoSnapshot);
        state.undoSnapshot = null;
        refreshAfterCollectionChange();
      },
    });
    return false;
  }
  if (!AixCollection.save(item)) {
    showToast("本机存储已满，收藏未写入");
    return false;
  }
  showToast("已加入收藏");
  return true;
}

function updateLibraryBadge() {
  const count = collectionRecords().length;
  document.querySelectorAll("[data-library-count]").forEach((node) => {
    node.hidden = count === 0;
    node.textContent = String(count);
  });
}

function setSaveButton(button, saved) {
  if (!button) return;
  button.classList.toggle("is-saved", saved);
  button.setAttribute("aria-pressed", String(saved));
  button.setAttribute("aria-label", saved ? "取消收藏" : "收藏这篇");
  button.textContent = saved ? "已收藏" : "收藏";
}

function refreshAfterCollectionChange() {
  updateLibraryBadge();
  if (page === "library") {
    renderLibrary();
    return;
  }
  document.querySelectorAll(".paper-card[data-id]").forEach((card) => {
    const item = findRenderableItem(card.dataset.id);
    if (!item) return;
    const saved = Boolean(savedRecord(item));
    setSaveButton(card.querySelector(".save-button"), saved);
    const noteBlock = card.querySelector(".note-block");
    if (noteBlock) noteBlock.hidden = !saved;
  });
}

function scheduleNoteSave(id, note, status) {
  window.clearTimeout(state.noteTimers[id]);
  if (status) status.textContent = "正在保存…";
  state.noteTimers[id] = window.setTimeout(() => {
    const saved = AixCollection.saveNote(id, note);
    if (status) status.textContent = saved === false ? "本机存储已满，笔记未写入" : "已保存在本机";
    if (page === "library") renderLibraryHero();
  }, 280);
}

function renderHeatmap() {
  const container = document.getElementById("activity-heatmap");
  if (!container) return;
  const viewing = currentDate();
  const signature = `${state.activity.length}:${[...state.archiveDates].join(",")}:${viewing}:${page}`;
  if (signature === state.heatmapSignature && container.childElementCount) return;
  state.heatmapSignature = signature;
  const fragment = document.createDocumentFragment();
  const relevant = state.activity.filter((item) => page === "home" || item.channel === channelId);
  const byDate = new Map();
  relevant.forEach((item) => {
    const existing = byDate.get(item.date) || { date: item.date, fetched: 0, candidates: 0, selected: 0 };
    existing.fetched += Number(item.fetched) || 0;
    existing.candidates += Number(item.candidates) || 0;
    existing.selected += Number(item.selected) || 0;
    byDate.set(item.date, existing);
  });
  const metric = state.activityMetric;
  const dates = [...byDate.keys()].sort();
  const latestDate = dates.at(-1) || state.payload?.date || dateKey(new Date());
  const firstDate = dates[0] || latestDate;
  const maximum = Math.max(0, ...[...byDate.values()].map((item) => item[metric] || 0));
  const end = dateFromKey(latestDate);
  end.setUTCDate(end.getUTCDate() + (6 - end.getUTCDay()));
  const start = dateFromKey(firstDate);
  start.setUTCDate(start.getUTCDate() - start.getUTCDay());
  const dayCount = Math.round((end - start) / 86400000) + 1;
  let previousMonth = -1;
  let populatedDays = 0;
  let total = 0;

  ["日", "一", "二", "三", "四", "五", "六"].forEach((label) => {
    const dow = document.createElement("span");
    dow.className = "heatmap__dow";
    dow.textContent = label;
    fragment.appendChild(dow);
  });

  for (let offset = 0; offset < dayCount; offset += 1) {
    const day = new Date(start);
    day.setUTCDate(start.getUTCDate() + offset);
    const key = dateKey(day);
    const item = byDate.get(key);
    const value = Number(item?.[metric]) || 0;
    const week = Math.floor(offset / 7);
    if (day.getUTCMonth() !== previousMonth && (offset === 0 || day.getUTCDate() <= 7)) {
      previousMonth = day.getUTCMonth();
      const month = document.createElement("span");
      month.className = "heatmap__month";
      month.style.setProperty("--week", week);
      month.textContent = `${day.getUTCMonth() + 1}月`;
      fragment.appendChild(month);
    }
    const hasArchive = page === "home" ? state.archiveDates.has(key) : Boolean(item);
    const clickable = hasArchive && value > 0;
    const cell = document.createElement(clickable ? "button" : "span");
    cell.className = "heatmap__day";
    cell.dataset.level = activityLevel(value, maximum);
    cell.dataset.date = key;
    cell.setAttribute("role", "gridcell");
    const label = `${formatDate(key)}：精选 ${value}`;
    cell.title = label;
    cell.setAttribute("aria-label", label);
    if (key === viewing) cell.classList.add("is-current");
    if (clickable) cell.type = "button";
    cell.tabIndex = -1;
    fragment.appendChild(cell);
    if (value > 0) populatedDays += 1;
    total += value;
  }
  container.replaceChildren(fragment);
  const days = [...container.querySelectorAll(".heatmap__day")];
  const currentIndex = days.findIndex((cell) => cell.classList.contains("is-current"));
  const fallback = days.findLastIndex((cell) => cell.tagName === "BUTTON");
  const focusIndex = currentIndex >= 0 ? currentIndex : Math.max(0, fallback);
  if (days[focusIndex]) days[focusIndex].tabIndex = 0;
  setText("activity-summary", `有记录 ${populatedDays} 天，合计 ${total.toLocaleString("zh-CN")} 项精选`);
  const scroller = container.closest(".heatmap-scroll");
  if (scroller) scroller.scrollLeft = scroller.scrollWidth;
}

function renderChannels() {
  const container = document.getElementById("channel-cards");
  if (!container || !state.manifest) return;
  container.replaceChildren();
  const date = requestedDate();
  state.manifest.channels.forEach((channel) => {
    const dailyChannel = state.payload?.channels?.find((item) => item.id === channel.id);
    const selected = dailyChannel
      ? Number(dailyChannel.stats?.selected ?? (dailyChannel.items || []).length ?? 0)
      : date
        ? 0
        : Number(channel.stats?.selected || 0);
    const card = document.createElement("a");
    card.className = "channel-card";
    card.href = withDate(path(`channels/${channel.id}/`), date);
    card.style.setProperty("--channel-accent", channel.accent || "#1b7d76");

    const picture = document.createElement("picture");
    const webp = document.createElement("source");
    webp.type = "image/webp";
    webp.srcset = path(`assets/art/${channel.id}.webp`);
    const art = document.createElement("img");
    art.className = "channel-card__art";
    art.src = path(`assets/art/${channel.id}.jpg`);
    art.alt = "";
    art.loading = "lazy";
    art.decoding = "async";
    art.fetchPriority = "low";
    art.width = 640;
    art.height = 360;
    picture.append(webp, art);

    const body = document.createElement("div");
    body.className = "channel-card__body";
    const top = document.createElement("div");
    top.className = "channel-card__top";
    const icon = document.createElement("img");
    icon.className = "channel-card__icon";
    icon.src = path(`assets/icons/${channel.id}.svg`);
    icon.alt = "";
    const title = document.createElement("h3");
    title.textContent = channel.name;
    const count = document.createElement("span");
    count.className = selected > 0 ? "channel-card__count" : "channel-card__count is-empty";
    count.textContent = selected > 0 ? `${selected} 项` : "暂无";
    top.append(icon, title, count);

    const description = document.createElement("p");
    description.textContent = channel.description;
    const meta = document.createElement("span");
    meta.className = "channel-card__meta";
    meta.textContent = (channel.sources || []).slice(0, 3).join(" · ");
    body.append(top, description, meta);
    card.append(picture, body);
    container.appendChild(card);
  });
}

function paperSearchText(item) {
  const cached = state.searchIndex.get(item);
  if (cached) return cached;
  const text = [
    displayTitle(item),
    item.summary_zh,
    item.why_it_matters_zh,
    item.abstract_zh,
    item.abstract_or_text,
    item.abstract,
    item.author_line,
    ...(item.creators || []),
    item.source,
    item.category,
    ...(item.tags || []),
  ].join(" ").toLocaleLowerCase("zh-CN");
  state.searchIndex.set(item, text);
  return text;
}

function visibleItems() {
  const query = state.query.trim().toLocaleLowerCase("zh-CN");
  return payloadItems().filter((item) => (
    (state.source === "all" || item.source === state.source)
    && (!query || paperSearchText(item).includes(query))
  ));
}

function abstractPair(item) {
  return {
    zh: (item.abstract_zh || "").trim(),
    en: (item.abstract_or_text || item.abstract || "").trim(),
  };
}

function applyAbstractLanguage(root, item, lang) {
  const pair = abstractPair(item);
  const chosen = lang === "en" ? (pair.en || pair.zh) : (pair.zh || pair.en);
  const text = root.querySelector(".abstract-text");
  if (text) setRichText(text, chosen || "该来源未提供摘要或正文。");
  root.querySelectorAll(".abstract-lang__btn").forEach((button) => {
    const active = button.dataset.lang === lang;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

function syncAbstractSummary(details) {
  const label = details.querySelector(".abstract-summary-label") || details.querySelector("summary");
  if (label) label.textContent = details.open ? "收起摘要" : "查看摘要";
}

function bindLangButtons(details) {
  if (!details || details.dataset.langBound === "1") return;
  details.dataset.langBound = "1";
  details.querySelectorAll(".abstract-lang__btn").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const lang = AixCollection.setAbstractLang(button.dataset.lang);
      document.querySelectorAll(".abstract-details").forEach((node) => {
        const card = node.closest(".paper-card");
        const current = findRenderableItem(card?.dataset.id);
        if (current) applyAbstractLanguage(node, current, lang);
      });
    });
  });
}

function bindPendingAbstract(details, abstract) {
  abstract.textContent = "正在载入摘要…";
  const toolbar = details.querySelector(".abstract-toolbar");
  if (toolbar) toolbar.hidden = true;
  details.addEventListener("toggle", () => {
    syncAbstractSummary(details);
    if (details.open) ensureHomeAbstracts();
  });
  syncAbstractSummary(details);
}

function bindAbstract(fragment, item) {
  const details = fragment.querySelector(".abstract-details");
  const abstract = fragment.querySelector(".abstract-text");
  if (!details || !abstract) return;
  const pair = abstractPair(item);
  if (!pair.zh && !pair.en) {
    if (page === "home" && homeNeedsAbstractHydration()) {
      bindPendingAbstract(details, abstract);
      return;
    }
    details.remove();
    return;
  }
  const toolbar = details.querySelector(".abstract-toolbar");
  if (toolbar && !(pair.zh && pair.en && pair.zh !== pair.en)) {
    toolbar.remove();
  }
  const preferred = AixCollection.abstractLang();
  const initial = preferred === "en" && pair.en ? "en" : (pair.zh ? "zh" : "en");
  applyAbstractLanguage(details, item, initial);
  syncAbstractSummary(details);
  details.addEventListener("toggle", () => syncAbstractSummary(details));
  bindLangButtons(details);
}

function createItemCard(item, groupName) {
  const fragment = document.getElementById("paper-template").content.cloneNode(true);
  const card = fragment.querySelector(".paper-card");
  const key = collectionItemKey(item);
  if (card && key) {
    card.dataset.id = key;
    card.id = itemAnchor(item);
  }
  const saved = savedRecord(item);
  setSaveButton(fragment.querySelector(".save-button"), Boolean(saved));
  const noteBlock = fragment.querySelector(".note-block");
  const noteField = fragment.querySelector(".note-field");
  if (noteBlock) {
    noteBlock.hidden = page !== "library" && !saved;
    if (noteField) {
      noteField.value = saved?.note || "";
      if (key) {
        noteField.id = `note-${key}`;
        const noteLabel = fragment.querySelector(".note-label");
        if (noteLabel) noteLabel.setAttribute("for", noteField.id);
      }
    }
  }
  const rank = fragment.querySelector(".rank");
  if (!item.rank) rank.remove();
  else rank.textContent = String(item.rank).padStart(2, "0");
  fragment.querySelector(".source-badge").textContent = item.source;
  const topic = fragment.querySelector(".topic-label");
  if (!item.category || item.category === groupName) topic.remove();
  else topic.textContent = item.category;
  const title = fragment.querySelector(".paper-title");
  title.href = item.url;
  setRichText(title, displayTitle(item));
  const openHint = document.createElement("span");
  openHint.className = "sr-only";
  openHint.textContent = "（在新窗口打开）";
  title.appendChild(openHint);
  fragment.querySelector(".paper-meta").textContent = `${formatAuthorLine(item)} · ${(item.published_at || item.published || "日期暂缺").slice(0, 10)}`;
  const summary = item.summary_zh || "中文说明暂缺，请查看原始内容。";
  setRichText(fragment.querySelector(".summary-zh"), summary);
  const why = fragment.querySelector(".why-it-matters");
  if (item.why_it_matters_zh && !sameText(item.why_it_matters_zh, item.summary_zh)) {
    setRichText(why, item.why_it_matters_zh);
  } else {
    why.remove();
  }
  bindAbstract(fragment, item);
  const tags = fragment.querySelector(".tag-list");
  [...new Set(item.tags || [])]
    .filter((tag) => tag && tag !== item.category && tag !== item.source)
    .slice(0, 6)
    .forEach((tag) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "tag";
      button.textContent = tag;
      button.setAttribute("aria-label", `按标签筛选：${tag}`);
      const active = page === "library"
        ? state.libraryTag === tag
        : state.query.trim() === tag;
      button.classList.toggle("is-active", active);
      tags.appendChild(button);
    });
  return fragment;
}

function emptyDayText() {
  const weekday = weekdayLabel(state.payload?.date);
  if (weekday === "星期日") return "星期日预印本源站通常没有新记录。可在上方打开历史日报。";
  return "这一天没有达到收录标准的更新。可在上方打开历史日报。";
}

function ensureEmptyArt() {
  const image = document.getElementById("empty-art");
  if (!image || image.getAttribute("src")) return;
  image.src = path("assets/art/empty.jpg");
  const webp = document.getElementById("empty-art-webp");
  if (webp) webp.srcset = path("assets/art/empty.webp");
}

function renderEmptyState(filteredCount) {
  const empty = document.getElementById("empty-state");
  const toolbar = document.querySelector(".toolbar");
  const allCount = payloadItems().length;
  empty.hidden = filteredCount > 0;
  if (filteredCount === 0) ensureEmptyArt();
  if (toolbar) toolbar.hidden = allCount === 0;
  if (filteredCount > 0) return;
  if (allCount === 0) {
    setText("empty-title", viewingHistory() ? "当日暂无精选" : "今日暂无精选");
    setText("empty-text", emptyDayText());
    return;
  }
  setText("empty-title", "没有匹配的内容");
  setText("empty-text", "请减少筛选条件或更换搜索词。");
}

function renderItems() {
  const items = visibleItems();
  const container = document.getElementById("paper-groups");
  const total = payloadItems().length;
  setText("result-count", total ? `显示 ${items.length} / ${total} 项` : "");
  renderEmptyState(items.length);
  const fragment = document.createDocumentFragment();
  const groups = new Map();
  items.forEach((item) => {
    const group = page === "home"
      ? (item.channel_name || channelNames[item.channel] || "其他更新")
      : (item.category || "当日收录");
    if (!groups.has(group)) groups.set(group, []);
    groups.get(group).push(item);
  });
  groups.forEach((values, name) => {
    const section = document.createElement("section");
    section.className = "paper-group";
    const title = document.createElement("h3");
    title.className = "group-title";
    title.append(document.createTextNode(name));
    const count = document.createElement("span");
    count.textContent = `${values.length} 项`;
    title.appendChild(count);
    section.appendChild(title);
    values.forEach((item) => section.appendChild(createItemCard(item, name)));
    fragment.appendChild(section);
  });
  container.replaceChildren(fragment);
  focusItemFromHash();
}

function formatAuthorLine(item) {
  const names = [...(item.creators || [])]
    .map((name) => String(name || "").trim())
    .filter(Boolean);
  if (names.length) return names.join(", ");
  const fallback = String(item.author_line || "").replace(/\s*等\s*\d+\s*人\s*$/u, "").trim();
  return fallback || "作者信息暂缺";
}

function configuredSources() {
  const channels = state.manifest?.channels || [];
  if (page === "home") {
    return channels.flatMap((channel) => channel.sources || []);
  }
  const current = channels.find((channel) => channel.id === channelId);
  return current?.sources || [];
}

function renderSourceFilters() {
  const container = document.getElementById("source-filters");
  if (!container) return;
  container.replaceChildren();
  const seen = new Set();
  const sources = [];
  for (const source of [...HUB_SOURCES, ...configuredSources(), ...payloadItems().map((item) => item.source)]) {
    if (!source || seen.has(source)) continue;
    seen.add(source);
    sources.push(source);
  }
  ["all", ...sources].forEach((source) => {
    const button = document.createElement("button");
    button.className = `filter-chip${source === state.source ? " is-active" : ""}`;
    button.type = "button";
    button.dataset.source = source;
    button.textContent = source === "all" ? "全部来源" : source;
    container.appendChild(button);
  });
}

function markChannelNav() {
  const date = requestedDate();
  document.querySelectorAll(".channel-nav__item").forEach((link) => {
    const href = link.getAttribute("href") || "";
    const isOverview = link.textContent.trim() === "总览";
    const active = page === "channel" ? href.includes(`/${channelId}`) || href.includes(`${channelId}/`) : isOverview;
    link.classList.toggle("is-active", active);
    if (active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
    if (!date) return;
    const base = href.split("?")[0];
    link.href = withDate(base, date);
  });
  const activeLink = document.querySelector(".channel-nav__item.is-active");
  const nav = activeLink?.closest(".channel-nav");
  if (activeLink && nav) {
    nav.scrollLeft = activeLink.offsetLeft - Math.max(0, (nav.clientWidth - activeLink.offsetWidth) / 2);
  }
}

function renderHero(payload) {
  const isHome = page === "home";
  const date = payload.date || "";
  const history = viewingHistory();
  document.title = isHome
    ? `${SITE_NAME} · ${date}`
    : `${channelNames[channelId] || SITE_NAME} · ${date}`;
  setText("digest-date", formatDate(date));
  const dateNode = document.getElementById("digest-date");
  if (dateNode) dateNode.dateTime = date;
  setText("hero-weekday", weekdayLabel(date));
  setText("eyebrow", isHome ? (history ? "历史日报" : "今日精选") : (channelNames[channelId] || "频道"));
  const title = document.getElementById("hero-title");
  if (title) {
    title.textContent = isHome
      ? (history ? "这一天的研究更新" : "今日研究更新")
      : (channelTitles[channelId] || channelNames[channelId] || payload.title || "每日精选");
  }
  setText("papers-title", history ? "当日内容" : "今日内容");
  const back = document.getElementById("back-to-today");
  if (back) {
    back.hidden = !history;
    back.href = page === "home" ? path("./") : "./";
  }
  setRichText(
    document.getElementById("subtitle"),
    isHome ? (payload.overview_zh || "") : (payload.subtitle || payload.overview_zh || ""),
  );
  setText("generated-time", formatGeneratedAt(payload.generated_at));
  const stats = isHome
    ? (payload.channels || []).reduce((acc, channel) => acc + Number(channel.stats?.selected || 0), 0)
    : payload.stats?.selected || payloadItems(payload).length;
  setText("stat-selected", Number(stats).toLocaleString("zh-CN"));
  setText("footer-date", date ? `${history ? "本期日期" : "最近更新"}：${formatDate(date)}` : "—");

  const artStem = isHome ? "hero" : channelId;
  const art = document.getElementById("hero-art");
  const artWebp = document.getElementById("hero-art-webp");
  if (art) art.src = path(`assets/art/${artStem}.jpg`);
  if (artWebp) artWebp.srcset = path(`assets/art/${artStem}.webp`);

  const note = document.getElementById("source-note");
  const errors = isHome
    ? (payload.channels || []).flatMap((channel) => channel.source_errors || [])
    : payload.source_errors || [];
  const message = friendlySourceNote(errors);
  if (note) {
    note.hidden = !message;
    note.textContent = message;
  }
}

function renderPayload(payload) {
  state.payload = payload;
  renderHero(payload);
  renderChannels();
  renderSourceFilters();
  renderItems();
  renderHeatmap();
  markChannelNav();
  scheduleActivityLoad();
}

function markHomeOnlySections() {
  document.querySelectorAll("[data-home-only]").forEach((element) => {
    element.hidden = page !== "home";
  });
}

async function loadManifest() {
  state.manifest = await loadJSON("api/v1/manifest.json", { priority: "high" });
  renderChannels();
  markChannelNav();
}

function scheduleActivityLoad() {
  if (state.activityScheduled) return;
  state.activityScheduled = true;
  const run = () => {
    loadJSON("api/v1/activity.json", { priority: "low" }).then((activity) => {
      state.activity = activity.items || [];
      renderHeatmap();
    }).catch((error) => {
      const summary = document.getElementById("activity-summary");
      if (summary) summary.textContent = `活动数据读取失败：${error.message}`;
    });
  };
  const target = document.querySelector(".activity-panel") || document.getElementById("activity-heatmap");
  if (!target || !("IntersectionObserver" in window)) {
    run();
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    if (!entries.some((entry) => entry.isIntersecting)) return;
    observer.disconnect();
    run();
  }, { rootMargin: "240px" });
  observer.observe(target);
}

async function loadArchive() {
  const container = document.getElementById("history-list");
  if (!container) return;
  const archivePath = page === "channel"
    ? `data/channels/${channelId}/archive/index.json`
    : "data/daily/archive/index.json";
  try {
    const value = await loadJSON(archivePath);
    const items = value.items || [];
    state.archiveDates = new Set(items.map((item) => item.date).filter(Boolean));
    const viewing = currentDate();
    const fragment = document.createDocumentFragment();
    items.forEach((item) => {
      const link = document.createElement("a");
      link.className = "history-link";
      if (item.date === viewing) {
        link.classList.add("is-current");
        link.setAttribute("aria-current", "page");
      }
      link.href = `?date=${encodeURIComponent(item.date)}`;
      link.append(document.createTextNode(formatDate(item.date)));
      const count = document.createElement("span");
      count.textContent = `${item.selected || 0} 项精选`;
      link.appendChild(count);
      fragment.appendChild(link);
    });
    container.replaceChildren(fragment);
    renderHeatmap();
  } catch (error) {
    container.textContent = `历史列表读取失败：${error.message}`;
  }
}

function flattenHomeItems(payload) {
  let rank = 0;
  payload.items = (payload.channels || []).flatMap((channel) => (
    (channel.items || channel.papers || []).map((item) => {
      rank += 1;
      return {
        ...item,
        rank,
        channel: item.channel || channel.id,
        channel_name: channel.name,
      };
    })
  ));
  return payload;
}

async function loadHomeDigest(date) {
  const url = date ? `data/daily/archive/${encodeURIComponent(date)}.json` : "data/daily/latest.json";
  try {
    return flattenHomeItems(await loadJSON(url, { priority: "high" }));
  } catch (error) {
    throw new Error(date ? `没有 ${date} 的综合日报` : error.message);
  }
}

function homeNeedsAbstractHydration(payload) {
  if (page !== "home") return false;
  const items = payloadItems(payload);
  return Boolean(items.length && !items.some((item) => item.abstract_or_text || item.abstract_zh));
}

async function hydrateHomeAbstracts(payload = state.payload) {
  if (!homeNeedsAbstractHydration(payload)) return false;
  const date = payload?.date || currentDate();
  if (!date) return false;
  try {
    const archive = await loadJSON(`data/daily/archive/${encodeURIComponent(date)}.json`, { priority: "low" });
    const byId = new Map();
    (archive.channels || []).forEach((channel) => {
      (channel.items || channel.papers || []).forEach((item) => {
        if (item?.id) byId.set(item.id, item);
      });
    });
    let changed = false;
    payloadItems(payload).forEach((item) => {
      const full = byId.get(item.id);
      if (!full) return;
      if (full.abstract_or_text) {
        item.abstract_or_text = full.abstract_or_text;
        changed = true;
      }
      if (full.abstract_zh) {
        item.abstract_zh = full.abstract_zh;
        changed = true;
      }
      const saved = savedRecord(item);
      if (saved && (item.abstract_or_text || item.abstract_zh)) {
        AixCollection.save(item, saved);
      }
    });
    if (changed) state.searchIndex = new WeakMap();
    return changed;
  } catch {
    return false;
  }
}

function mountAbstract(card, item) {
  if (!card || !item || card.querySelector(".abstract-details")) return;
  const template = document.getElementById("paper-template")?.content.querySelector(".abstract-details");
  if (!template) return;
  const details = template.cloneNode(true);
  const body = card.querySelector(".paper-card__body");
  const note = card.querySelector(".note-block");
  if (!body) return;
  if (note) body.insertBefore(details, note);
  else body.appendChild(details);
  bindAbstract(card, item);
}

function refreshRenderedAbstracts() {
  document.querySelectorAll(".paper-card[data-id]").forEach((card) => {
    const item = findRenderableItem(card.dataset.id);
    if (!item) return;
    const pair = abstractPair(item);
    const details = card.querySelector(".abstract-details");
    if (!pair.zh && !pair.en) {
      const text = details?.querySelector(".abstract-text");
      if (text && text.textContent === "正在载入摘要…") {
        text.textContent = "该来源未提供摘要或正文。";
      }
      return;
    }
    if (!details) {
      mountAbstract(card, item);
      return;
    }
    const toolbar = details.querySelector(".abstract-toolbar");
    if (toolbar) {
      if (pair.zh && pair.en && pair.zh !== pair.en) toolbar.hidden = false;
      else toolbar.remove();
    }
    const preferred = AixCollection.abstractLang();
    applyAbstractLanguage(details, item, preferred === "en" && pair.en ? "en" : (pair.zh ? "zh" : "en"));
    bindLangButtons(details);
    if (details.open) syncAbstractSummary(details);
  });
}

function ensureHomeAbstracts() {
  if (!homeNeedsAbstractHydration()) return Promise.resolve(false);
  if (state.abstractsPromise) return state.abstractsPromise;
  state.abstractsPromise = hydrateHomeAbstracts().then((changed) => {
    refreshRenderedAbstracts();
    if (state.query.trim()) renderItems();
    if (!changed && homeNeedsAbstractHydration()) state.abstractsPromise = null;
    return changed;
  });
  return state.abstractsPromise;
}

function scheduleAbstractHydration() {
  if (page !== "home" || !homeNeedsAbstractHydration()) return;
  if (navigator.connection?.saveData) return;
  const start = () => ensureHomeAbstracts();
  window.setTimeout(() => {
    if (window.requestIdleCallback) window.requestIdleCallback(start, { timeout: 1500 });
    else start();
  }, 800);
}

async function loadDigest() {
  const date = requestedDate();
  const payload = page === "home"
    ? await loadHomeDigest(date)
    : await loadJSON(date
      ? `data/channels/${channelId}/archive/${encodeURIComponent(date)}.json`
      : `data/channels/${channelId}/latest.json`, { priority: "high" });
  renderPayload(payload);
  scheduleAbstractHydration();
  focusItemFromHash();
}

function findRenderableItem(id) {
  return payloadItems().find((item) => collectionItemKey(item) === id) || AixCollection.read().items[id] || null;
}

function bindCollectionEvents(rootId) {
  const rootNode = document.getElementById(rootId);
  if (!rootNode) return;
  rootNode.addEventListener("click", (event) => {
    const copy = event.target.closest(".copy-link");
    if (copy) {
      const card = copy.closest(".paper-card");
      const item = findRenderableItem(card?.dataset.id);
      if (item) copyItemLink(item);
      return;
    }
    const tag = event.target.closest("button.tag");
    if (tag) {
      const value = tag.textContent.trim();
      if (!value) return;
      if (page === "library") {
        state.libraryTag = state.libraryTag === value ? "all" : value;
        renderLibrary();
        return;
      }
      const input = document.getElementById("search-input");
      state.query = state.query.trim() === value ? "" : value;
      if (input) input.value = state.query;
      renderItems();
      return;
    }
    const button = event.target.closest(".save-button");
    if (!button) return;
    const card = button.closest(".paper-card");
    const item = findRenderableItem(card?.dataset.id);
    if (!item) return;
    const saved = toggleSaved(item);
    setSaveButton(button, saved);
    const noteBlock = card.querySelector(".note-block");
    const noteField = card.querySelector(".note-field");
    if (noteBlock && page !== "library") {
      noteBlock.hidden = !saved;
      if (saved && noteField && !noteField.value) {
        noteField.value = savedRecord(item)?.note || "";
        noteField.focus();
      }
    }
    if (page === "library") renderLibrary();
  });
  rootNode.addEventListener("input", (event) => {
    const field = event.target.closest(".note-field");
    if (!field) return;
    const card = field.closest(".paper-card");
    if (!card?.dataset.id || !savedRecord({ id: card.dataset.id })) return;
    scheduleNoteSave(card.dataset.id, field.value, card.querySelector(".note-status"));
  });
}

function visibleLibraryRecords() {
  const query = state.libraryQuery.trim().toLocaleLowerCase("zh-CN");
  return collectionRecords().filter((record) => {
    const tags = recordTags(record);
    const channelMatch = state.libraryChannel === "all" || record.channel === state.libraryChannel;
    const tagMatch = state.libraryTag === "all"
      || (state.libraryTag === UNTAGGED_LABEL ? tags.length === 0 : tags.includes(state.libraryTag));
    if (!channelMatch || !tagMatch) return false;
    if (!query) return true;
    const haystack = [
      record.title,
      record.note,
      record.summary_zh,
      record.abstract_zh,
      record.abstract_or_text,
      record.source,
      record.author_line,
      ...(record.creators || []),
      record.category,
      record.channel_name,
      ...(record.tags || []),
    ].join(" ").toLocaleLowerCase("zh-CN");
    return haystack.includes(query);
  });
}

function renderLibraryHero() {
  const records = collectionRecords();
  setText("library-total", String(records.length));
  setText("library-note-count", String(records.filter((record) => (record.note || "").trim()).length));
}

function renderRail(containerId, options, selected, dataKey) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const fragment = document.createDocumentFragment();
  options.forEach(([value, label, count]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `tag-rail__item${selected === value ? " is-active" : ""}`;
    button.dataset[dataKey] = value;
    button.append(document.createTextNode(label));
    const badge = document.createElement("span");
    badge.textContent = String(count);
    button.appendChild(badge);
    fragment.appendChild(button);
  });
  container.replaceChildren(fragment);
}

function renderLibraryRails(records) {
  const channelOptions = [["all", "全部", records.length]];
  AixCollection.CHANNEL_ORDER.forEach((id) => {
    const count = records.filter((record) => record.channel === id).length;
    if (count) channelOptions.push([id, AixCollection.channelName(id), count]);
  });
  const extras = [...new Set(records.map((record) => record.channel).filter((id) => id && !AixCollection.CHANNEL_ORDER.includes(id)))];
  extras.forEach((id) => {
    const count = records.filter((record) => record.channel === id).length;
    channelOptions.push([id, AixCollection.channelName(id, id), count]);
  });
  renderRail("channel-rail", channelOptions, state.libraryChannel, "channel");
  const scoped = state.libraryChannel === "all"
    ? records
    : records.filter((record) => record.channel === state.libraryChannel);
  const tagOptions = [["all", "全部", scoped.length], ...tagCounts(scoped).map(([tag, count]) => [tag, tag, count])];
  renderRail("tag-rail", tagOptions, state.libraryTag, "tag");
}

function libraryHeading() {
  if (state.libraryTag !== "all") return state.libraryTag;
  if (state.libraryChannel !== "all") return AixCollection.channelName(state.libraryChannel);
  return "全部收藏";
}

function renderLibrary() {
  const records = collectionRecords();
  if (state.libraryChannel !== "all" && !records.some((record) => record.channel === state.libraryChannel)) {
    state.libraryChannel = "all";
  }
  if (state.libraryTag !== "all") {
    const scoped = state.libraryChannel === "all"
      ? records
      : records.filter((record) => record.channel === state.libraryChannel);
    const tags = new Set(scoped.flatMap((record) => {
      const values = recordTags(record);
      return values.length ? values : [UNTAGGED_LABEL];
    }));
    if (!tags.has(state.libraryTag)) state.libraryTag = "all";
  }
  const visible = visibleLibraryRecords();
  renderLibraryHero();
  renderLibraryRails(records);
  updateLibraryBadge();
  const title = document.getElementById("library-title");
  if (title) title.textContent = libraryHeading();
  setText("library-result-count", records.length ? `显示 ${visible.length} / ${records.length} 篇` : "");
  const empty = document.getElementById("library-empty");
  const groups = document.getElementById("library-groups");
  if (empty) {
    empty.hidden = visible.length > 0;
    if (visible.length === 0) {
      ensureEmptyArt();
      setText("empty-title", records.length ? "没有匹配的收藏" : "还没有收藏");
      setText("empty-text", records.length
        ? "请更换频道、标签或搜索词。"
        : "在日报条目右上角点「收藏」，条目会按所属频道归入这里。笔记只保存在本机。");
    }
  }
  if (!groups) return;
  if (!visible.length) {
    groups.replaceChildren();
    return;
  }
  const grouped = new Map();
  if (state.libraryChannel === "all" && state.libraryTag === "all") {
    AixCollection.CHANNEL_ORDER.forEach((id) => {
      const values = visible.filter((record) => record.channel === id);
      if (values.length) grouped.set(AixCollection.channelName(id), values);
    });
    const leftover = visible.filter((record) => !AixCollection.CHANNEL_ORDER.includes(record.channel));
    if (leftover.length) grouped.set("其他更新", leftover);
  } else {
    grouped.set(libraryHeading(), visible);
  }
  const fragment = document.createDocumentFragment();
  grouped.forEach((values, name) => {
    const section = document.createElement("section");
    section.className = "paper-group";
    const heading = document.createElement("h3");
    heading.className = "group-title";
    heading.append(document.createTextNode(name));
    const count = document.createElement("span");
    count.textContent = `${values.length} 篇`;
    heading.appendChild(count);
    section.appendChild(heading);
    values.forEach((record, index) => {
      section.appendChild(createItemCard({ ...record, rank: index + 1 }, name));
    });
    fragment.appendChild(section);
  });
  groups.replaceChildren(fragment);
  focusItemFromHash();
}

function bindDebouncedSearch(inputId, apply) {
  const input = document.getElementById(inputId);
  if (!input) return;
  let timer = 0;
  const run = () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(apply, 120);
  };
  input.addEventListener("compositionstart", () => {
    input.dataset.composing = "1";
  });
  input.addEventListener("compositionend", () => {
    delete input.dataset.composing;
    apply();
  });
  input.addEventListener("input", (event) => {
    if (event.isComposing || input.dataset.composing === "1") return;
    run();
  });
}

function bindLibraryPage() {
  bindDebouncedSearch("library-search", () => {
    state.libraryQuery = document.getElementById("library-search")?.value || "";
    renderLibrary();
  });
  document.getElementById("channel-rail")?.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-channel]");
    if (!button) return;
    state.libraryChannel = button.dataset.channel;
    state.libraryTag = "all";
    renderLibrary();
  });
  document.getElementById("tag-rail")?.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-tag]");
    if (!button) return;
    state.libraryTag = button.dataset.tag;
    renderLibrary();
  });
  document.getElementById("export-collection")?.addEventListener("click", () => {
    AixCollection.exportBackup();
    showToast("已下载收藏备份");
  });
  document.getElementById("import-collection")?.addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    const status = document.getElementById("library-status");
    if (!file) return;
    try {
      const payload = JSON.parse(await file.text());
      if (!AixCollection.mergeBackup(payload)) throw new Error("write failed");
      renderLibrary();
      if (status) {
        status.hidden = false;
        status.textContent = "备份已合并到本机收藏。";
      }
      showToast("备份已合并到本机收藏");
    } catch {
      if (status) {
        status.hidden = false;
        status.textContent = "导入失败：请选择由本站导出的 JSON 备份。";
      }
    }
    event.target.value = "";
  });
  bindCollectionEvents("library-groups");
}

function bindGlobalShortcuts() {
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      const historyButton = document.getElementById("history-button");
      const historyPanel = document.getElementById("history-panel");
      if (historyPanel && !historyPanel.hidden) {
        historyButton?.setAttribute("aria-expanded", "false");
        historyPanel.hidden = true;
        historyButton?.focus();
        return;
      }
      const active = document.activeElement;
      if (active && (active.id === "search-input" || active.id === "library-search")) {
        if (active.value) {
          active.value = "";
          active.dispatchEvent(new Event("input", { bubbles: true }));
        } else {
          active.blur();
        }
      }
      return;
    }
    if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey) return;
    const target = event.target;
    const typing = target && (
      target.tagName === "INPUT"
      || target.tagName === "TEXTAREA"
      || target.isContentEditable
    );
    if (typing) return;
    const input = document.getElementById("search-input") || document.getElementById("library-search");
    if (!input) return;
    event.preventDefault();
    input.focus();
    input.select();
  });
}

function bindEvents() {
  bindDebouncedSearch("search-input", () => {
    state.query = document.getElementById("search-input")?.value || "";
    if (state.query.trim()) ensureHomeAbstracts();
    renderItems();
  });
  document.getElementById("source-filters")?.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-source]");
    if (!button) return;
    state.source = button.dataset.source;
    document.querySelectorAll("button[data-source]").forEach((item) => item.classList.toggle("is-active", item === button));
    renderItems();
  });
  document.getElementById("activity-heatmap")?.addEventListener("click", (event) => {
    const cell = event.target.closest("button.heatmap__day[data-date]");
    if (!cell) return;
    location.href = `?date=${encodeURIComponent(cell.dataset.date)}`;
  });
  document.getElementById("activity-heatmap")?.addEventListener("keydown", (event) => {
    const cells = [...document.querySelectorAll("#activity-heatmap .heatmap__day")];
    const current = cells.indexOf(document.activeElement);
    if (current < 0) return;
    const delta = { ArrowUp: -1, ArrowDown: 1, ArrowLeft: -7, ArrowRight: 7 }[event.key];
    if (delta) {
      event.preventDefault();
      const next = Math.max(0, Math.min(cells.length - 1, current + delta));
      cells.forEach((cell, index) => {
        cell.tabIndex = index === next ? 0 : -1;
      });
      cells[next].focus();
      cells[next].scrollIntoView({ block: "nearest", inline: "nearest" });
      return;
    }
    if (event.key === "Home") {
      event.preventDefault();
      const start = current - (current % 7);
      cells.forEach((cell, index) => {
        cell.tabIndex = index === start ? 0 : -1;
      });
      cells[start]?.focus();
      return;
    }
    if (event.key === "End") {
      event.preventDefault();
      const end = Math.min(cells.length - 1, current - (current % 7) + 6);
      cells.forEach((cell, index) => {
        cell.tabIndex = index === end ? 0 : -1;
      });
      cells[end]?.focus();
      return;
    }
    if ((event.key === "Enter" || event.key === " ") && document.activeElement?.tagName === "BUTTON") {
      event.preventDefault();
      document.activeElement.click();
    }
  });
  const historyButton = document.getElementById("history-button");
  const historyPanel = document.getElementById("history-panel");
  const closeHistory = () => {
    if (!historyButton || !historyPanel) return;
    historyButton.setAttribute("aria-expanded", "false");
    historyPanel.hidden = true;
  };
  historyButton?.addEventListener("click", () => {
    const open = historyButton.getAttribute("aria-expanded") === "true";
    historyButton.setAttribute("aria-expanded", String(!open));
    historyPanel.hidden = open;
    if (!open) {
      window.requestAnimationFrame(() => {
        historyPanel.querySelector(".is-current")?.scrollIntoView({ block: "nearest" });
      });
    }
  });
  document.addEventListener("click", (event) => {
    if (!historyPanel || historyPanel.hidden) return;
    if (historyPanel.contains(event.target) || historyButton.contains(event.target)) return;
    closeHistory();
  });
  bindCollectionEvents("paper-groups");
}

function showLoadError(error) {
  const container = document.getElementById("paper-groups");
  if (!container) return;
  container.replaceChildren();
  const box = document.createElement("div");
  box.className = "empty-state";
  const title = document.createElement("strong");
  title.textContent = "日报数据暂时无法读取";
  const text = document.createElement("p");
  text.textContent = error.message;
  box.append(title, text);
  container.appendChild(box);
}

markHomeOnlySections();
updateLibraryBadge();
bindGlobalShortcuts();
window.addEventListener("hashchange", focusItemFromHash);
window.addEventListener("aix-collection-change", updateLibraryBadge);
if (page === "library") {
  bindLibraryPage();
  renderLibrary();
} else {
  bindEvents();
  loadDigest().catch(showLoadError);
  loadManifest().catch(() => {});
  loadArchive();
}
