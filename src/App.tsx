import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Bookmark,
  BrainCircuit,
  CalendarDays,
  Check,
  ChevronDown,
  ChevronRight,
  Circle,
  Code2,
  Files,
  GraduationCap,
  Layers,
  LayoutGrid,
  MessageSquare,
  Minus,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Search,
  Settings,
  Square,
  X,
} from "lucide-react";
import {
  addTab,
  closeTab,
  MAX_TABS,
  navigate,
  tabTitle,
  type Subject,
  type Topic,
  type View,
} from "./model";
import { useWorkspace } from "./storage/useWorkspace";
import { Materials } from "./Materials";
import { StorageSettings } from "./StorageSettings";
import { useJobs } from "./storage/useJobs";
import { useImports } from "./storage/useImports";
import { JobPanel } from "./JobPanel";

const icons = {
  probability: BrainCircuit,
  algebra: LayoutGrid,
  code: Code2,
  book: BookOpen,
};
type Go = (view: View, subjectId?: string, topicId?: string) => void;

export function App() {
  const storage = useWorkspace();
  const { session, setSession, workspace } = storage;
  const imports = useImports();
  const queue = useJobs(workspace.id, storage.ready);
  const [notice, setNotice] = useState("");
  const [dialog, setDialog] = useState<
    "workspace" | "subject" | "topic" | null
  >(null);
  const [maximized, setMaximized] = useState(false);
  const active = session.tabs.find((tab) => tab.id === session.activeTabId)!;
  const subject = session.subjects.find((item) => item.id === active.subjectId);
  const topic = subject?.topics.find((item) => item.id === active.topicId);
  const go: Go = (view, subjectId, topicId) => {
    if (storage.ready)
      setSession((previous) => navigate(previous, view, subjectId, topicId));
  };
  const openTab = useCallback(() => {
    if (!storage.ready) return;
    if (session.tabs.length >= MAX_TABS) {
      setNotice(
        "You have 12 study tabs open. Close one before opening another.",
      );
      return;
    }
    setSession(addTab);
  }, [session.tabs.length, storage.ready]);
  useEffect(() => window.studyLens?.onMaximized(setMaximized), []);
  useEffect(() => {
    function handle(event: KeyboardEvent) {
      if (!(event.ctrlKey || event.metaKey) || dialog || !storage.ready) return;
      if (event.key.toLowerCase() === "t") {
        event.preventDefault();
        openTab();
      }
      if (event.key.toLowerCase() === "w") {
        event.preventDefault();
        setSession((previous) => closeTab(previous, previous.activeTabId));
      }
      if (event.key.toLowerCase() === "b") {
        event.preventDefault();
        setSession((previous) => ({
          ...previous,
          sidebarCollapsed: !previous.sidebarCollapsed,
        }));
      }
      if (event.key === "Tab") {
        event.preventDefault();
        setSession((previous) => {
          const index = previous.tabs.findIndex(
            (tab) => tab.id === previous.activeTabId,
          );
          const next =
            (index + (event.shiftKey ? -1 : 1) + previous.tabs.length) %
            previous.tabs.length;
          return { ...previous, activeTabId: previous.tabs[next].id };
        });
      }
    }
    window.addEventListener("keydown", handle);
    return () => window.removeEventListener("keydown", handle);
  }, [dialog, openTab, storage.ready]);

  async function createItem(name: string) {
    if (!storage.ready)
      return "Connect to the local service before creating items.";
    const clean = name.trim();
    if (dialog === "workspace") {
      try {
        await storage.createWorkspace(clean);
      } catch (error) {
        return error instanceof Error
          ? error.message
          : "Workspace could not be created.";
      }
    } else if (dialog === "subject") {
      if (
        session.subjects.some(
          (item) => item.name.toLowerCase() === clean.toLowerCase(),
        )
      )
        return "A subject with this name already exists.";
      if (session.subjects.length >= 100)
        return "This workspace already contains 100 subjects.";
      const item: Subject = {
        id: crypto.randomUUID(),
        name: clean,
        icon: "book",
        topics: [],
        demo: false,
      };
      setSession((previous) =>
        navigate(
          { ...previous, subjects: [...previous.subjects, item] },
          "topics",
          item.id,
        ),
      );
    } else if (subject) {
      if (
        subject.topics.some(
          (item) => item.title.toLowerCase() === clean.toLowerCase(),
        )
      )
        return "A topic with this name already exists.";
      if (subject.topics.length >= 300)
        return "This subject already contains 300 topics.";
      const item: Topic = {
        id: crypto.randomUUID(),
        title: clean,
        description: "Add course material to build this topic.",
        unit: "Your topics",
        read: false,
      };
      setSession((previous) => ({
        ...previous,
        subjects: previous.subjects.map((current) =>
          current.id === subject.id
            ? { ...current, topics: [...current.topics, item] }
            : current,
        ),
      }));
    }
    setDialog(null);
    return null;
  }

  return (
    <div
      className={`app ${session.sidebarCollapsed ? "sidebar-collapsed" : ""}`}
    >
      <header className="titlebar">
        <div className="brand">
          <span className="brand-mark">
            <GraduationCap size={15} />
          </span>
          <span>Neev</span>
        </div>
        <div className="window-actions">
          {!window.studyLens && (
            <span className="preview-label">Browser preview</span>
          )}
          <button
            aria-label="Minimize window"
            disabled={!window.studyLens}
            onClick={() => window.studyLens?.windowAction("minimize")}
          >
            <Minus size={14} />
          </button>
          <button
            aria-label={maximized ? "Restore window" : "Maximize window"}
            disabled={!window.studyLens}
            onClick={() => window.studyLens?.windowAction("maximize")}
          >
            <Square size={12} />
          </button>
          <button
            className="window-close"
            aria-label="Close window"
            disabled={!window.studyLens}
            onClick={() => window.studyLens?.windowAction("close")}
          >
            <X size={14} />
          </button>
        </div>
      </header>
      <div className="tabstrip">
        <div className="study-tabs" role="tablist" aria-label="Study tabs">
          {session.tabs.map((tab) => (
            <div
              className={`study-tab ${tab.id === active.id ? "active" : ""}`}
              key={tab.id}
            >
              <button
                role="tab"
                aria-selected={tab.id === active.id}
                aria-controls="study-panel"
                id={`tab-${tab.id}`}
                disabled={!storage.ready}
                onClick={() =>
                  setSession((previous) => ({
                    ...previous,
                    activeTabId: tab.id,
                  }))
                }
              >
                {tab.view === "workspace" ? (
                  <Circle size={13} />
                ) : tab.view === "ask" ? (
                  <MessageSquare size={13} />
                ) : (
                  <BookOpen size={13} />
                )}
                <span>{tabTitle(tab, session.subjects)}</span>
              </button>
              <button
                className="close-tab"
                disabled={!storage.ready}
                aria-label={`Close ${tabTitle(tab, session.subjects)} tab`}
                onClick={() =>
                  setSession((previous) => closeTab(previous, tab.id))
                }
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
        <button
          className="new-tab icon-button"
          aria-label="New study tab"
          title="New study tab (Ctrl+T)"
          disabled={!storage.ready}
          onClick={openTab}
        >
          <Plus size={17} />
        </button>
      </div>
      <div className="body-shell">
        <aside className="sidebar" aria-label="Study navigation">
          <div className="sidebar-top">
            <div className="workspace-select">
              <Layers size={15} />
              <select
                aria-label="Current workspace"
                value={workspace.id}
                disabled={!storage.ready}
                onChange={(event) => {
                  void storage
                    .switchWorkspace(event.target.value)
                    .catch((error) => setNotice(error.message));
                }}
              >
                {storage.workspaces.length ? (
                  storage.workspaces.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))
                ) : (
                  <option value={workspace.id}>{workspace.name}</option>
                )}
              </select>
              <button
                className="icon-button"
                aria-label="Create workspace"
                title="Create workspace"
                disabled={!storage.ready}
                onClick={() => setDialog("workspace")}
              >
                <Plus size={13} />
              </button>
            </div>
            <button
              className={`nav-item ${active.view === "workspace" ? "selected" : ""}`}
              onClick={() => go("workspace")}
            >
              <LayoutGrid size={15} />
              <span>Workspace</span>
            </button>
            <button
              className={`nav-item ${active.view === "today" ? "selected" : ""}`}
              onClick={() => go("today")}
            >
              <CalendarDays size={15} />
              <span>Today</span>
            </button>
            <div className="nav-heading">
              Subjects
              <button
                aria-label="Create subject"
                disabled={!storage.ready}
                onClick={() => setDialog("subject")}
              >
                <Plus size={13} />
              </button>
            </div>
            {session.subjects.map((item) => {
              const Icon = icons[item.icon];
              return (
                <button
                  key={item.id}
                  className={`nav-item ${subject?.id === item.id ? "selected" : ""}`}
                  onClick={() => go("topics", item.id)}
                >
                  <Icon size={15} />
                  <span>{item.name}</span>
                </button>
              );
            })}
            <div className="nav-heading">Topics</div>
            {subject ? (
              subject.topics.length ? (
                subject.topics.map((item) => (
                  <button
                    className={`nav-item topic-nav ${topic?.id === item.id ? "selected" : ""}`}
                    key={item.id}
                    onClick={() => go("learn", subject.id, item.id)}
                  >
                    <Circle size={10} />
                    <span>{item.title}</span>
                  </button>
                ))
              ) : (
                <p className="rail-note">
                  Add your first topic to this subject.
                </p>
              )
            ) : (
              <p className="rail-note">Select a subject to see its topics.</p>
            )}
            {subject && (
              <button
                className={`nav-item ${active.view === "materials" ? "selected" : ""}`}
                onClick={() => go("materials", subject.id)}
              >
                <Files size={15} />
                <span>Subject materials</span>
              </button>
            )}
          </div>
          <div className="sidebar-bottom">
            <button
              className={`nav-item ${active.view === "settings" ? "selected" : ""}`}
              onClick={() => go("settings")}
            >
              <Settings size={15} />
              <span>Settings</span>
            </button>
          </div>
        </aside>
        <main
          id="study-panel"
          role="tabpanel"
          aria-labelledby={`tab-${active.id}`}
          className="main-panel"
        >
          <div className="context-bar">
            <button
              className="icon-button"
              disabled={!storage.ready}
              title="Toggle sidebar (Ctrl+B)"
              aria-label={
                session.sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"
              }
              onClick={() =>
                setSession((previous) => ({
                  ...previous,
                  sidebarCollapsed: !previous.sidebarCollapsed,
                }))
              }
            >
              {session.sidebarCollapsed ? (
                <PanelLeftOpen size={17} />
              ) : (
                <PanelLeftClose size={17} />
              )}
            </button>
            <nav aria-label="Breadcrumb" className="breadcrumbs">
              <button onClick={() => go("workspace")}>{workspace.name}</button>
              {subject && (
                <>
                  <ChevronRight size={12} />
                  <button onClick={() => go("topics", subject.id)}>
                    {subject.name}
                  </button>
                </>
              )}
              {topic && (
                <>
                  <ChevronRight size={12} />
                  <span>{topic.title}</span>
                </>
              )}
            </nav>
            <span className={`save-state ${storage.status}`} role="status">
              {storage.status === "saved"
                ? "Saved on this device"
                : storage.status === "saving"
                  ? "Saving…"
                  : storage.status === "loading"
                    ? "Connecting…"
                    : "Needs attention"}
            </span>
          </div>
          {storage.error && (
            <div className="notice storage-notice" role="alert">
              <span>{storage.error}</span>
              <button
                className="text-button"
                onClick={() => void storage.retry()}
              >
                Retry
              </button>
              {storage.status === "conflict" && (
                <button
                  className="text-button"
                  onClick={() => void storage.loadSaved()}
                >
                  Load saved workspace
                </button>
              )}
            </div>
          )}
          {notice && (
            <div className="notice" role="status">
              <span>{notice}</span>
              <button
                aria-label="Dismiss notification"
                onClick={() => setNotice("")}
              >
                <X size={14} />
              </button>
            </div>
          )}
          <JobPanel queue={queue} imports={imports} />
          <div
            className="content-scroll"
            key={workspace.id + active.id + active.view + (topic?.id ?? "")}
          >
            {active.view === "workspace" && (
              <Workspace
                subjects={session.subjects}
                name={workspace.name}
                ready={storage.ready}
                go={go}
                create={() => setDialog("subject")}
              />
            )}
            {active.view === "topics" && subject && (
              <SubjectView
                subject={subject}
                ready={storage.ready}
                go={go}
                addTopic={() => setDialog("topic")}
              />
            )}
            {["learn", "ask", "practice"].includes(active.view) && subject && (
              <>
                <div className="activity-toolbar">
                  <button
                    className="text-button"
                    onClick={() => go("topics", subject.id)}
                  >
                    <ArrowLeft size={15} /> Topics
                  </button>
                  <div className="activity-tabs" aria-label="Topic activities">
                    {(["learn", "ask", "practice"] as const).map((view) => (
                      <button
                        key={view}
                        className={active.view === view ? "active" : ""}
                        disabled={view === "learn" && !topic}
                        onClick={() => go(view, subject.id, topic?.id)}
                      >
                        {view === "learn"
                          ? "Learn"
                          : view === "ask"
                            ? "Ask"
                            : "Practice"}
                      </button>
                    ))}
                  </div>
                  {subject.demo && (
                    <span className="small-tag">Demo curriculum</span>
                  )}
                </div>
                {active.view === "learn" && topic && (
                  <Lesson
                    topic={topic}
                    ready={storage.ready}
                    onRead={() =>
                      setSession((previous) => ({
                        ...previous,
                        subjects: previous.subjects.map((item) =>
                          item.id === subject.id
                            ? {
                                ...item,
                                topics: item.topics.map((current) =>
                                  current.id === topic.id
                                    ? { ...current, read: !current.read }
                                    : current,
                                ),
                              }
                            : item,
                        ),
                      }))
                    }
                    ask={() => go("ask", subject.id, topic.id)}
                  />
                )}
                {active.view === "ask" && (
                  <div className="ask-view">
                    <div className="ask-empty">
                      <span className="empty-symbol">
                        <MessageSquare size={25} />
                      </span>
                      <h1>Ask about {topic?.title ?? subject.name}</h1>
                      <p>
                        Your questions will be answered with evidence from your
                        course materials.
                      </p>
                      <div className="availability-note">
                        Grounded tutoring arrives in Phase 9. You can write and
                        save a question here now.
                      </div>
                    </div>
                    <div className="composer">
                      <textarea
                        disabled={!storage.ready}
                        aria-label="Question draft"
                        placeholder={`Write a question about ${topic?.title ?? subject.name}…`}
                        maxLength={20000}
                        value={active.draft}
                        onChange={(event) =>
                          setSession((previous) => ({
                            ...previous,
                            tabs: previous.tabs.map((tab) =>
                              tab.id === active.id
                                ? { ...tab, draft: event.target.value }
                                : tab,
                            ),
                          }))
                        }
                      />
                      <div className="composer-footer">
                        <span>
                          {storage.status === "saved"
                            ? "Draft saved on this device"
                            : storage.status === "saving"
                              ? "Saving draft…"
                              : "Draft not yet saved"}
                        </span>
                        <button
                          className="primary"
                          disabled
                          title="Grounded tutoring arrives in Phase 9"
                        >
                          Ask <ArrowRight size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                )}
                {active.view === "practice" && (
                  <EmptyView
                    icon="practice"
                    title="Practice with your materials"
                    text="Verified quizzes and mock exams arrive in Phase 11. Topic mastery stays Not assessed until there is reliable evidence."
                    action="View subject materials"
                    onAction={() => go("materials", subject.id)}
                  />
                )}
              </>
            )}
            {active.view === "materials" && subject && (
              <Materials
                workspaceId={workspace.id}
                subject={subject}
                ready={storage.ready}
                flush={storage.flush}
                imports={imports}
                queue={queue}
                back={() => go("topics", subject.id)}
              />
            )}
            {active.view === "today" && (
              <EmptyView
                icon="today"
                title="Make room for a little progress"
                text="Your personalized study plan arrives in Phase 16. For now, choose a subject and pick a topic to explore."
                action="Explore subjects"
                onAction={() => go("workspace")}
              />
            )}
            {active.view === "settings" && (
              <div className="settings-page">
                <p className="eyebrow">Your workspace</p>
                <h1>Settings</h1>
                <StorageSettings />
                <section className="settings-section">
                  <h2>Background work</h2>
                  <p>
                    Saved materials are checked by one background worker. You
                    can keep studying while it runs, cancel a job, or resume an
                    interrupted job.
                  </p>
                  {queue.status?.evaluation_enabled && (
                    <div className="queue-eval-tools">
                      <p className="small-text">
                        Evaluation mode · this test does not process course
                        content or change mastery.
                      </p>
                      <button
                        className="secondary"
                        onClick={() => void queue.action("test")}
                      >
                        Run slow queue test
                      </button>
                    </div>
                  )}
                </section>
                <section className="settings-section">
                  <h2>Keyboard shortcuts</h2>
                  <div className="info-row">
                    <span>New study tab</span>
                    <kbd>Ctrl + T</kbd>
                  </div>
                  <div className="info-row">
                    <span>Close active tab</span>
                    <kbd>Ctrl + W</kbd>
                  </div>
                  <div className="info-row">
                    <span>Switch study tabs</span>
                    <kbd>Ctrl + Tab</kbd>
                  </div>
                  <div className="info-row">
                    <span>Toggle sidebar</span>
                    <kbd>Ctrl + B</kbd>
                  </div>
                </section>
              </div>
            )}
          </div>
        </main>
      </div>
      {dialog && (
        <CreateDialog
          kind={dialog}
          onClose={() => setDialog(null)}
          onSubmit={createItem}
        />
      )}
    </div>
  );
}

function Workspace({
  subjects,
  name,
  ready,
  go,
  create,
}: {
  subjects: Subject[];
  name: string;
  ready: boolean;
  go: Go;
  create: () => void;
}) {
  const [why, setWhy] = useState(false);
  const sample = subjects.find((subject) => subject.id === "probability");
  const recommendation = sample?.topics.find(
    (topic) => topic.id === "conditional",
  );
  return (
    <div className="workspace-page" data-testid="workspace">
      <div className="page-heading">
        <p className="eyebrow">{name} workspace</p>
        <h1>Your next study session</h1>
        <p>Pick up a topic, or make space for something new.</p>
      </div>
      {sample && recommendation && (
        <section className="recommendation">
          <div className="recommendation-main">
            <div>
              <p className="eyebrow">A place to start</p>
              <h2>Explore: Conditional probability</h2>
              <p>Build the foundations for Bayes’ theorem.</p>
            </div>
            <button
              className="primary"
              onClick={() => go("learn", sample.id, recommendation.id)}
            >
              Start studying <ArrowRight size={15} />
            </button>
          </div>
          <button
            className="why-link"
            aria-expanded={why}
            onClick={() => setWhy(!why)}
          >
            {why ? <ChevronDown size={13} /> : <ChevronRight size={13} />} Why
            recommended?
          </button>
          {why && (
            <p className="why-explanation">
              This is a suggested starting point from the demo curriculum, not a
              personalized mastery prediction. Recommendations will use your
              assessment history in Phase 12.
            </p>
          )}
        </section>
      )}
      <div className="workspace-columns">
        <section>
          <div className="section-heading">
            <h2>Your subjects</h2>
            <span>{subjects.length} subjects</span>
          </div>
          <div className="subject-list">
            {subjects.map((subject) => {
              const Icon = icons[subject.icon];
              return (
                <button
                  className="subject-row"
                  key={subject.id}
                  onClick={() => go("topics", subject.id)}
                >
                  <span className="subject-icon">
                    <Icon size={19} />
                  </span>
                  <span className="subject-row-info">
                    <strong>{subject.name}</strong>
                    <span>
                      {subject.topics.length} topics
                      {subject.demo ? " · Demo curriculum" : ""}
                    </span>
                  </span>
                  <span className="status-neutral">
                    <Circle size={9} /> Not assessed
                  </span>
                  <ChevronRight size={14} />
                </button>
              );
            })}
          </div>
        </section>
        <section className="today-summary">
          <div className="section-heading">
            <h2>Today</h2>
            <CalendarDays size={16} />
          </div>
          <p className="today-lead">A plan that fits your day.</p>
          <p>
            Your schedule will appear here once your exam goals and available
            time are set.
          </p>
          <button className="text-button" onClick={() => go("today")}>
            View study plan <ArrowRight size={14} />
          </button>
          <span className="small-text">Scheduling arrives in Phase 16</span>
        </section>
      </div>
      <div className="workspace-actions">
        <button className="secondary" onClick={create} disabled={!ready}>
          <Plus size={15} /> Create subject
        </button>
        <span>Keep each course in its own space.</span>
      </div>
    </div>
  );
}

function SubjectView({
  subject,
  ready,
  go,
  addTopic,
}: {
  subject: Subject;
  ready: boolean;
  go: Go;
  addTopic: () => void;
}) {
  const units = [...new Set(subject.topics.map((topic) => topic.unit))];
  return (
    <div className="subject-page">
      <div className="subject-heading">
        <div>
          <p className="eyebrow">
            Your subject{subject.demo ? " · Demo curriculum" : ""}
          </p>
          <h1>{subject.name}</h1>
        </div>
        <button className="primary" onClick={() => go("ask", subject.id)}>
          <MessageSquare size={15} /> Ask Neev
        </button>
      </div>
      <div className="subject-tabs">
        <button className="active">Topics</button>
        <button onClick={() => go("materials", subject.id)}>Materials</button>
        <button
          className="add-topic text-button"
          onClick={addTopic}
          disabled={!ready}
        >
          <Plus size={14} /> Add topic
        </button>
      </div>
      {!subject.topics.length && (
        <div className="inline-empty">
          <BookOpen size={29} />
          <h2>Your first topic starts here</h2>
          <p>
            Organize what you want to study. Your materials will help fill in
            the detail later.
          </p>
          <button className="secondary" onClick={addTopic} disabled={!ready}>
            Add a topic
          </button>
        </div>
      )}
      {units.map((unit, index) => (
        <section className="topic-unit" key={unit}>
          <div className="unit-heading">
            <h2>
              Unit {index + 1}: {unit}
            </h2>
            <span>
              {
                subject.topics.filter(
                  (topic) => topic.unit === unit && topic.read,
                ).length
              }{" "}
              / {subject.topics.filter((topic) => topic.unit === unit).length}{" "}
              marked read
            </span>
          </div>
          <div className="topic-grid">
            {subject.topics
              .filter((topic) => topic.unit === unit)
              .map((topic) => (
                <button
                  key={topic.id}
                  className="topic-card"
                  onClick={() => go("learn", subject.id, topic.id)}
                >
                  <div className="topic-card-heading">
                    <h3>{topic.title}</h3>
                    <ArrowRight size={15} />
                  </div>
                  <p>{topic.description}</p>
                  <div className="topic-card-footer">
                    <span>
                      {topic.read ? (
                        <>
                          <Check size={12} /> Marked read
                        </>
                      ) : topic.lesson && topic.readMinutes ? (
                        `${topic.readMinutes} min · Demo lesson`
                      ) : (
                        "No material added"
                      )}
                    </span>
                    <span className="status-neutral">Not assessed</span>
                  </div>
                </button>
              ))}
          </div>
        </section>
      ))}
      <p className="small-text subject-footnote">
        Reading completion and topic mastery are tracked separately. Every topic
        is open to you.
      </p>
    </div>
  );
}

function Lesson({
  topic,
  ready,
  onRead,
  ask,
}: {
  topic: Topic;
  ready: boolean;
  onRead: () => void;
  ask: () => void;
}) {
  return (
    <article className="lesson">
      <div className="lesson-meta">
        <span className="status-neutral">
          <Circle size={9} /> Not assessed
        </span>
        <button
          className={`secondary read-toggle ${topic.read ? "is-read" : ""}`}
          aria-pressed={topic.read}
          disabled={!topic.lesson || !ready}
          title={topic.lesson ? undefined : "Add reading material first"}
          onClick={onRead}
        >
          {topic.read ? <Check size={14} /> : <Bookmark size={14} />}{" "}
          {topic.read ? "Marked as read" : "Mark as read"}
        </button>
      </div>
      <h1>{topic.title}</h1>
      <p className="lesson-intro">{topic.description}</p>
      {topic.lesson === "conditional" ? (
        <>
          <div className="demo-note">
            <BookOpen size={14} />
            <span>
              Demo lesson · authored sample content, not retrieved from uploaded
              material.
            </span>
          </div>
          <p>
            Conditional probability is the probability of an event occurring,
            given that another event has already occurred. The condition changes
            which outcomes we consider.
          </p>
          <div className="formula-block">
            <div className="formula">P(A | B) = P(A ∩ B) / P(B)</div>
            <p>
              The probability of A given B equals the probability of both events
              divided by the probability of B, provided P(B) &gt; 0.
            </p>
          </div>
          <h2>Start with the sample space</h2>
          <p>
            Imagine drawing one card uniformly from a standard 52-card deck.
            Before you know anything else, there are 52 possible cards. Four are
            aces, so P(ace) = 4/52 = 1/13.
          </p>
          <h2>Now add a condition</h2>
          <p>
            You are told that the card is a spade. Only 13 possible cards
            remain, and exactly one is an ace. So P(ace | spade) = 1/13.
          </p>
          <div className="lesson-callout">
            <strong>The key idea</strong>
            <p>
              The denominator is the set of outcomes that satisfy the condition.
              In this example, conditioning narrows the sample space even though
              the probability of an ace happens to stay the same.
            </p>
          </div>
          <h2>Order matters</h2>
          <p>
            P(spade | ace) = 1/4, because one of the four aces is a spade. That
            is different from P(ace | spade) = 1/13. Always ask: which event is
            the condition?
          </p>
          <button className="secondary" onClick={ask}>
            <MessageSquare size={15} /> Save a question about this topic
          </button>
        </>
      ) : (
        <div className="inline-empty">
          <Files size={29} />
          <h2>Bring your material to this topic</h2>
          <p>
            This topic is ready for your notes and course sources. Only
            Conditional Probability currently has an authored demo lesson.
          </p>
          <button className="secondary" onClick={ask}>
            Save a question
          </button>
        </div>
      )}
      <p className="reading-note">
        Marking a topic as read records completion. It does not change your
        mastery.
      </p>
    </article>
  );
}

function EmptyView({
  icon,
  eyebrow,
  title,
  text,
  action,
  onAction,
  children,
}: {
  icon: "materials" | "today" | "practice";
  eyebrow?: string;
  title: string;
  text: string;
  action: string;
  onAction: () => void;
  children?: React.ReactNode;
}) {
  const Icon =
    icon === "materials" ? Files : icon === "today" ? CalendarDays : Search;
  return (
    <div className="empty-view">
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      <span className="empty-symbol">
        <Icon size={29} />
      </span>
      <h1>{title}</h1>
      <p>{text}</p>
      {children}
      <button className="secondary" onClick={onAction}>
        {action}
        <ArrowRight size={14} />
      </button>
    </div>
  );
}

function CreateDialog({
  kind,
  onClose,
  onSubmit,
}: {
  kind: "workspace" | "subject" | "topic";
  onClose: () => void;
  onSubmit: (name: string) => Promise<string | null>;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    ref.current?.showModal();
    ref.current?.querySelector("input")?.focus();
    return () => ref.current?.close();
  }, []);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) {
      setError(`Enter a ${kind} name.`);
      return;
    }
    setBusy(true);
    const result = await onSubmit(name);
    setBusy(false);
    if (result) setError(result);
  }
  return (
    <dialog
      ref={ref}
      className="create-dialog"
      aria-labelledby="create-title"
      onCancel={onClose}
    >
      <form onSubmit={submit}>
        <div className="dialog-heading">
          <h2 id="create-title">Create {kind}</h2>
          <button
            type="button"
            className="icon-button"
            aria-label="Close dialog"
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </div>
        <p>
          {kind === "workspace"
            ? "Keep a semester or study goal in its own workspace."
            : kind === "subject"
              ? "Give your course its own space."
              : "Choose one concept or section to study."}
        </p>
        <label htmlFor="item-name">
          {kind === "workspace"
            ? "Workspace name"
            : kind === "subject"
              ? "Subject name"
              : "Topic name"}
        </label>
        <input
          id="item-name"
          autoFocus
          autoComplete="off"
          maxLength={kind === "topic" ? 100 : 60}
          placeholder={
            kind === "workspace"
              ? "e.g. Semester 4"
              : kind === "subject"
                ? "e.g. Discrete Mathematics"
                : "e.g. Combinatorics"
          }
          value={name}
          onChange={(event) => {
            setName(event.target.value);
            setError("");
          }}
          aria-invalid={!!error}
          aria-describedby={error ? "create-error" : undefined}
        />
        {error && (
          <p className="form-error" role="alert" id="create-error">
            {error}
          </p>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="primary" type="submit" disabled={busy}>
            {busy ? "Creating…" : `Create ${kind}`}
          </button>
        </div>
      </form>
    </dialog>
  );
}
