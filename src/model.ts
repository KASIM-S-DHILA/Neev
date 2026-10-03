export type View =
  | "workspace"
  | "topics"
  | "learn"
  | "ask"
  | "practice"
  | "materials"
  | "today"
  | "settings";
export type Topic = {
  id: string;
  title: string;
  description: string;
  unit: string;
  readMinutes?: number;
  lesson?: "conditional";
  read: boolean;
};
export type Subject = {
  id: string;
  name: string;
  icon: "probability" | "algebra" | "code" | "book";
  topics: Topic[];
  demo: boolean;
};
export type StudyTab = {
  id: string;
  view: View;
  subjectId?: string;
  topicId?: string;
  draft: string;
};
export type Session = {
  version: 1;
  tabs: StudyTab[];
  activeTabId: string;
  subjects: Subject[];
  sidebarCollapsed: boolean;
};
export const SESSION_KEY = "studylens.session.v1";
export const MAX_TABS = 12;
const views: View[] = [
  "workspace",
  "topics",
  "learn",
  "ask",
  "practice",
  "materials",
  "today",
  "settings",
];

export function defaultSubjects(): Subject[] {
  return [
    {
      id: "probability",
      name: "Probability",
      icon: "probability",
      demo: true,
      topics: [
        {
          id: "sample-space",
          title: "Sample Spaces & Events",
          description:
            "Defining sets of outcomes and understanding basic event operations.",
          unit: "Fundamentals",
          readMinutes: 12,
          read: false,
        },
        {
          id: "conditional",
          title: "Conditional Probability",
          description:
            "Calculating probability given partial information about outcomes.",
          unit: "Fundamentals",
          readMinutes: 8,
          lesson: "conditional",
          read: false,
        },
        {
          id: "bayes",
          title: "Bayes’ Theorem",
          description:
            "Updating probability estimates as new evidence becomes available.",
          unit: "Advanced theorems",
          readMinutes: 15,
          read: false,
        },
        {
          id: "independence",
          title: "Independence",
          description: "Understanding when one event does not affect another.",
          unit: "Advanced theorems",
          readMinutes: 10,
          read: false,
        },
      ],
    },
    {
      id: "linear-algebra",
      name: "Linear Algebra",
      icon: "algebra",
      demo: true,
      topics: [
        {
          id: "vectors",
          title: "Vectors & Spaces",
          description:
            "Build intuition for vectors and the spaces they live in.",
          unit: "Foundations",
          read: false,
        },
        {
          id: "matrices",
          title: "Matrices",
          description: "Represent transformations with matrices.",
          unit: "Foundations",
          read: false,
        },
      ],
    },
    {
      id: "data-structures",
      name: "Data Structures",
      icon: "code",
      demo: true,
      topics: [
        {
          id: "arrays",
          title: "Arrays & Lists",
          description: "Organize sequences and understand their trade-offs.",
          unit: "Foundations",
          read: false,
        },
        {
          id: "trees",
          title: "Trees",
          description: "Explore hierarchical structures and traversal.",
          unit: "Foundations",
          read: false,
        },
      ],
    },
  ];
}

export function newTab(): StudyTab {
  return { id: crypto.randomUUID(), view: "workspace", draft: "" };
}
export function initialSession(): Session {
  const tab = newTab();
  return {
    version: 1,
    tabs: [tab],
    activeTabId: tab.id,
    subjects: defaultSubjects(),
    sidebarCollapsed: false,
  };
}
export function addTab(session: Session): Session {
  if (session.tabs.length >= MAX_TABS) return session;
  const tab = newTab();
  return { ...session, tabs: [...session.tabs, tab], activeTabId: tab.id };
}
export function closeTab(session: Session, id: string): Session {
  const index = session.tabs.findIndex((tab) => tab.id === id);
  if (index < 0) return session;
  const tabs = session.tabs.filter((tab) => tab.id !== id);
  if (!tabs.length) {
    const tab = newTab();
    return { ...session, tabs: [tab], activeTabId: tab.id };
  }
  return {
    ...session,
    tabs,
    activeTabId:
      session.activeTabId === id
        ? tabs[Math.min(index, tabs.length - 1)].id
        : session.activeTabId,
  };
}
export function navigate(
  session: Session,
  view: View,
  subjectId?: string,
  topicId?: string,
): Session {
  return {
    ...session,
    tabs: session.tabs.map((tab) =>
      tab.id === session.activeTabId
        ? {
            ...tab,
            view,
            subjectId,
            topicId,
            draft:
              tab.subjectId === subjectId && tab.topicId === topicId
                ? tab.draft
                : "",
          }
        : tab,
    ),
  };
}
export function tabTitle(tab: StudyTab, subjects: Subject[]): string {
  if (tab.view === "workspace") return "New Tab";
  if (tab.view === "today") return "Today";
  if (tab.view === "settings") return "Settings";
  const subject = subjects.find((item) => item.id === tab.subjectId);
  const topic = subject?.topics.find((item) => item.id === tab.topicId);
  if (tab.view === "learn") return topic?.title ?? "Learn";
  const label = {
    topics: "Topics",
    materials: "Materials",
    ask: "Ask",
    practice: "Practice",
  }[tab.view];
  return `${subject?.name ?? "Subject"} · ${label}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}
function isString(value: unknown, max = 200): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= max;
}
export function restoreSession(raw: string | null): Session | null {
  if (!raw || raw.length > 1_000_000) return null;
  try {
    const value: unknown = JSON.parse(raw);
    if (
      !isRecord(value) ||
      value.version !== 1 ||
      !Array.isArray(value.subjects) ||
      !Array.isArray(value.tabs) ||
      !isString(value.activeTabId) ||
      typeof value.sidebarCollapsed !== "boolean"
    )
      return null;
    if (
      !value.tabs.length ||
      value.tabs.length > MAX_TABS ||
      value.subjects.length > 100
    )
      return null;
    for (const subject of value.subjects) {
      if (
        !isRecord(subject) ||
        !isString(subject.id) ||
        !isString(subject.name, 60) ||
        !["probability", "algebra", "code", "book"].includes(
          String(subject.icon),
        ) ||
        typeof subject.demo !== "boolean" ||
        !Array.isArray(subject.topics) ||
        subject.topics.length > 300
      )
        return null;
      for (const topic of subject.topics) {
        if (
          !isRecord(topic) ||
          !isString(topic.id) ||
          !isString(topic.title, 100) ||
          typeof topic.description !== "string" ||
          topic.description.length > 500 ||
          !isString(topic.unit, 80) ||
          typeof topic.read !== "boolean" ||
          (topic.lesson !== undefined && topic.lesson !== "conditional") ||
          (topic.readMinutes !== undefined &&
            (typeof topic.readMinutes !== "number" ||
              !Number.isFinite(topic.readMinutes) ||
              topic.readMinutes < 0))
        )
          return null;
      }
      if (
        new Set(subject.topics.map((topic) => topic.id)).size !==
        subject.topics.length
      )
        return null;
    }
    const subjects = value.subjects as Subject[];
    if (new Set(subjects.map((subject) => subject.id)).size !== subjects.length)
      return null;
    for (const tab of value.tabs) {
      if (
        !isRecord(tab) ||
        !isString(tab.id) ||
        !views.includes(tab.view as View) ||
        typeof tab.draft !== "string" ||
        tab.draft.length > 20000
      )
        return null;
      const subject = subjects.find((item) => item.id === tab.subjectId);
      if (tab.subjectId !== undefined && !subject) return null;
      if (
        tab.topicId !== undefined &&
        !subject?.topics.some((topic) => topic.id === tab.topicId)
      )
        return null;
      if (
        !["workspace", "today", "settings"].includes(tab.view as string) &&
        !subject
      )
        return null;
      if (tab.view === "learn" && tab.topicId === undefined) return null;
    }
    const tabs = value.tabs as StudyTab[];
    if (
      new Set(tabs.map((tab) => tab.id)).size !== tabs.length ||
      !tabs.some((tab) => tab.id === value.activeTabId)
    )
      return null;
    return value as Session;
  } catch {
    return null;
  }
}
