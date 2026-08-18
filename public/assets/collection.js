const AixCollection = (() => {
  const KEY = "aix-daily.collection.v1";
  const LANG_KEY = "aix-daily.abstract-lang.v1";
  const UNTAGGED = "未分类";
  const CHANNEL_ORDER = ["aixchem", "aixbio", "aixmath", "aivoices", "engineering"];
  const CHANNEL_NAMES = {
    aixchem: "AI × Chem",
    aixbio: "AI × Bio",
    aixmath: "AI × Math",
    aivoices: "AI Voices",
    engineering: "Engineering",
  };

  function empty() {
    return { schema_version: 1, updated_at: "", items: {}, notes: {} };
  }

  function read() {
    try {
      const value = JSON.parse(localStorage.getItem(KEY) || "");
      if (!value || typeof value.items !== "object" || Array.isArray(value.items)) return empty();
      if (!value.notes || typeof value.notes !== "object" || Array.isArray(value.notes)) value.notes = {};
      Object.entries(value.items).forEach(([id, item]) => {
        if (item?.note && !value.notes[id]) {
          value.notes[id] = { note: item.note, note_updated_at: item.note_updated_at || "" };
        }
      });
      return value;
    } catch {
      return empty();
    }
  }

  function notify() {
    window.dispatchEvent(new CustomEvent("aix-collection-change"));
  }

  function write(collection) {
    try {
      collection.updated_at = new Date().toISOString();
      localStorage.setItem(KEY, JSON.stringify(collection));
      notify();
      return true;
    } catch {
      return false;
    }
  }

  function key(item) {
    return String(item?.id || item?.url || "").trim();
  }

  function record(item) {
    return read().items[key(item)] || null;
  }

  function records() {
    return Object.values(read().items).sort((left, right) => (
      String(right.saved_at || "").localeCompare(String(left.saved_at || ""))
    ));
  }

  function channelName(id, fallback) {
    return CHANNEL_NAMES[id] || fallback || "其他更新";
  }

  function titleOf(item) {
    if (typeof window.displayTitle === "function") return window.displayTitle(item);
    return String(item?.title || "").trim() || "未命名条目";
  }

  function toRecord(item, existing) {
    const channel = item.channel || existing?.channel || document.body.dataset.channel || "";
    return {
      id: key(item),
      title: titleOf(item),
      url: item.url || existing?.url || "",
      source: item.source || existing?.source || "",
      channel,
      channel_name: item.channel_name || existing?.channel_name || channelName(channel),
      category: item.category || existing?.category || "",
      tags: [...new Set((item.tags || existing?.tags || []).filter(Boolean))],
      author_line: item.author_line || existing?.author_line || "",
      published: String(item.published_at || item.published || existing?.published || "").slice(0, 10),
      summary_zh: item.summary_zh || existing?.summary_zh || "",
      why_it_matters_zh: item.why_it_matters_zh || existing?.why_it_matters_zh || "",
      abstract_or_text: item.abstract_or_text || item.abstract || existing?.abstract_or_text || "",
      abstract_zh: item.abstract_zh || existing?.abstract_zh || "",
      saved_at: existing?.saved_at || new Date().toISOString(),
      note: existing?.note || "",
      note_updated_at: existing?.note_updated_at || "",
    };
  }

  function tagsOf(record) {
    const tags = [];
    if (record.category) tags.push(record.category);
    (record.tags || []).forEach((tag) => {
      if (tag && !tags.includes(tag)) tags.push(tag);
    });
    return tags;
  }

  function save(item, existing) {
    const id = key(item);
    if (!id) return null;
    const collection = read();
    const kept = collection.notes[id];
    const previous = existing || collection.items[id] || (kept
      ? { note: kept.note, note_updated_at: kept.note_updated_at }
      : null);
    collection.items[id] = toRecord(item, previous);
    if (!write(collection)) return null;
    return collection.items[id];
  }

  function remove(item) {
    const id = key(item);
    if (!id) return null;
    const collection = read();
    const current = collection.items[id];
    if (!current) return null;
    if (current.note) {
      collection.notes[id] = { note: current.note, note_updated_at: current.note_updated_at || "" };
    }
    delete collection.items[id];
    if (!write(collection)) return null;
    return current;
  }

  function restore(snapshot) {
    if (!snapshot) return null;
    return save(snapshot, snapshot);
  }

  function toggle(item) {
    return record(item) ? (remove(item) ? false : true) : Boolean(save(item));
  }

  function saveNote(id, note) {
    const collection = read();
    const current = collection.items[id];
    if (!current) return false;
    current.note = note;
    current.note_updated_at = new Date().toISOString();
    collection.notes[id] = { note: current.note, note_updated_at: current.note_updated_at };
    return write(collection);
  }

  function exportBackup() {
    const blob = new Blob([JSON.stringify(read(), null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    const now = new Date();
    const stamp = `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, "0")}-${String(now.getUTCDate()).padStart(2, "0")}`;
    link.href = URL.createObjectURL(blob);
    link.download = `aix-daily-collection-${stamp}.json`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function mergeBackup(payload) {
    const incomingItems = payload?.items && !Array.isArray(payload.items) ? payload.items : {};
    const incomingNotes = payload?.notes && !Array.isArray(payload.notes) ? payload.notes : {};
    const collection = read();
    Object.values(incomingItems).forEach((item) => {
      const id = key(item);
      if (!id) return;
      const previous = collection.items[id];
      if (!previous) {
        collection.items[id] = toRecord(item, item);
        return;
      }
      const keepIncomingNote = String(item.note_updated_at || "") >= String(previous.note_updated_at || "");
      collection.items[id] = {
        ...toRecord(item, previous),
        saved_at: previous.saved_at || item.saved_at,
        note: keepIncomingNote ? String(item.note || "") : previous.note,
        note_updated_at: keepIncomingNote ? (item.note_updated_at || previous.note_updated_at) : previous.note_updated_at,
      };
    });
    Object.entries(incomingNotes).forEach(([id, entry]) => {
      const incoming = entry?.note || "";
      const incomingAt = entry?.note_updated_at || "";
      const previous = collection.notes[id];
      if (!previous || String(incomingAt) >= String(previous.note_updated_at || "")) {
        collection.notes[id] = { note: incoming, note_updated_at: incomingAt };
      }
      if (collection.items[id] && String(incomingAt) >= String(collection.items[id].note_updated_at || "")) {
        collection.items[id].note = incoming;
        collection.items[id].note_updated_at = incomingAt;
      }
    });
    return write(collection);
  }

  function abstractLang() {
    try {
      const value = localStorage.getItem(LANG_KEY);
      return value === "en" ? "en" : "zh";
    } catch {
      return "zh";
    }
  }

  function setAbstractLang(lang) {
    const value = lang === "en" ? "en" : "zh";
    try {
      localStorage.setItem(LANG_KEY, value);
    } catch {
      /* ignore quota */
    }
    return value;
  }

  return {
    KEY,
    LANG_KEY,
    UNTAGGED,
    CHANNEL_ORDER,
    CHANNEL_NAMES,
    empty,
    read,
    write,
    key,
    record,
    records,
    channelName,
    tagsOf,
    toRecord,
    save,
    remove,
    restore,
    toggle,
    saveNote,
    exportBackup,
    mergeBackup,
    abstractLang,
    setAbstractLang,
  };
})();
