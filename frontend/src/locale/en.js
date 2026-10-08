// ALL user-facing strings live in this single locale file (English only for
// now) so a future language can be added without touching components.
export const t = {
  appName: "StudiousBrat",
  menu: "Menu",

  // Sidebar
  newTopic: "New topic",
  sessions: "Past sessions",
  untitledSession: "New session",
  active: "active",
  ended: "ended",
  settings: "Settings",
  whatWeStore: "What we store",

  // Composer
  inputPlaceholder: "Teach me a topic, or ask a question…",
  send: "Send",
  endSession: "End session",
  endConfirm: "End this session? Your history stays saved.",
  exportPdf: "Export PDF",

  // States
  thinking: "Thinking…",
  errorGeneric: "I'm having trouble right now — try again in a moment.",
  notSaved: "Not saved yet — will retry with your next message",
  emptyStateTitle: "What would you like to learn?",
  emptyStateBody:
    "Name any topic — photosynthesis, supply and demand, how a bill becomes law — and I'll break it down, bring an analogy, then you teach it back to me.",

  // Onboarding
  onboardingTitle: "Welcome to StudiousBrat",
  onboardingBody: "Tell me a little about you so explanations land at the right level.",
  nameLabel: "Your name (optional)",
  gradeLabel: "Grade level",
  selectPlaceholder: "Choose your grade",
  gradeOptions: [
    "Grade 4",
    "Grade 5",
    "Grade 6",
    "Grade 7",
    "Grade 8",
    "Grade 9",
    "Grade 10",
    "Grade 11",
    "Grade 12",
  ],
  subjectsLabel: "Subjects you're studying (comma-separated, optional)",
  subjectsHint: "e.g. biology, history, physics",
  universeLabel: "Favorite universe for analogies",
  universeHint: "e.g. cricket, Spider-Man, cooking, football",
  startButton: "Start learning",

  // Settings
  saveButton: "Save",
  cancelButton: "Cancel",
  gotItButton: "Got it",
  deleteMyData: "Delete my data",
  deleteConfirm:
    "This permanently deletes your profile and every session, message, evaluation and asset. Continue?",

  // Inline assets
  flashcardsTitle: "Flashcards",
  tapToFlip: "Tap to flip",
  flowchartTitle: "How it flows",
  memesTitle: "Memory hooks",
  teachBackTitle: "Teach-back check",
  covered: "You covered",
  missing: "Still missing",

  // Privacy
  privacyBody:
    "StudiousBrat stores your profile (name, grade level, subjects, preferred analogy universe), your sessions and messages, evaluations of your teach-back attempts, and generated assets (explanations, flashcards, flowcharts, memory hooks, PDFs).\n\nData is kept indefinitely until you delete it. There are no analytics tables and no third-party trackers.\n\nYou can delete everything at any time with 'Delete my data' in Settings — one click removes your profile and every session, message, evaluation and asset linked to it.",
};
