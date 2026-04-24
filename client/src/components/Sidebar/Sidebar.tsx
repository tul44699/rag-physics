import { useState } from 'react';
import { useGeneratedContent } from '../../context/GeneratedContentContext';
import { useTextbook } from '../../context/TextbookContext';
import ProfilePanel from './ProfilePanel';
import SidebarTabs, { type TabId } from './SidebarTabs';
import ChatTab from './ChatTab';
import FlashcardsTab from './FlashcardsTab';
import StudyGuidesTab from './StudyGuidesTab';
import SummariesTab from './SummariesTab';
import FormulasTab from './FormulasTab';
import styles from './Sidebar.module.css';

const TABS: { id: TabId; label: string }[] = [
  { id: 'chat', label: 'Chat' },
  { id: 'flashcards', label: 'Cards' },
  { id: 'studyGuides', label: 'Guides' },
  { id: 'summaries', label: 'Summary' },
  { id: 'formulas', label: 'Formulas' },
];

export default function Sidebar() {
  const [active, setActive] = useState<TabId>('chat');
  const { currentTextbookId } = useTextbook();
  const { getForTextbook } = useGeneratedContent();
  const content = currentTextbookId ? getForTextbook(currentTextbookId) : null;

  const tabsWithBadges = TABS.map((tab) => {
    let badge: number | undefined;
    if (tab.id === 'flashcards') badge = content?.flashcards.length;
    else if (tab.id === 'studyGuides') badge = content?.studyGuides.length;
    else if (tab.id === 'summaries') badge = content?.chapterSummaries.length;
    return { ...tab, badge };
  });

  return (
    <div className={styles.sidebar}>
      <ProfilePanel />
      <SidebarTabs active={active} tabs={tabsWithBadges} onChange={setActive} />
      <div className={styles.tabContent}>
        {active === 'chat' && <ChatTab />}
        {active === 'flashcards' && <FlashcardsTab />}
        {active === 'studyGuides' && <StudyGuidesTab />}
        {active === 'summaries' && <SummariesTab />}
        {active === 'formulas' && <FormulasTab />}
      </div>
    </div>
  );
}
