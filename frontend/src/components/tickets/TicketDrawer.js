import React from 'react';
import useTicketDrawer from '../../hooks/useTicketDrawer';
import CustomerHistoryPanel from './CustomerHistoryPanel';
import TicketConversation from './TicketConversation';
import TicketDetailsPanel from './TicketDetailsPanel';
import MergeTicketModal from './MergeTicketModal';
import LinkTicketModal from './LinkTicketModal';
import SplitTicketModal from './SplitTicketModal';
import FeatureRequestModal from './FeatureRequestModal';
import CannedResponsePicker from '../common/CannedResponsePicker';
import KnowledgeBasePicker from '../common/KnowledgeBasePicker';

const TicketDrawer = ({ ticket, users, currentUser, isOpen, onClose, onUpdate, onDelete, onTicketSwitch }) => {
  const state = useTicketDrawer({ ticket, users, currentUser, isOpen, onClose, onUpdate, onDelete });

  if ((!isOpen && !state.isClosing) || !ticket) return null;

  return (
    <>
      {/* Backdrop with fade animation */}
      <div
        className={`fixed inset-0 bg-black/70 backdrop-blur-sm z-50 transition-opacity duration-200 ${
          state.isClosing ? 'opacity-0' : 'opacity-100 animate-in fade-in duration-200'
        }`}
        onClick={state.handleCloseWithAnimation}
        data-testid="drawer-backdrop"
      />

      {/* Three-Panel Drawer with slide animation */}
      <div
        className={`fixed right-0 top-0 bottom-0 z-[60] flex shadow-2xl transition-transform duration-200 ease-out ${
          state.isClosing ? 'translate-x-full' : 'translate-x-0 animate-in slide-in-from-right duration-300'
        }`}
        style={{ width: 'calc(100vw - 220px)', maxWidth: '1200px' }}
        data-testid="ticket-drawer"
      >
        {/* Left Panel - Customer Ticket History */}
        <CustomerHistoryPanel
          ticket={ticket}
          users={users}
          relatedTickets={state.relatedTickets}
          loadingRelated={state.loadingRelated}
          assignee={state.assignee}
          getStatusConfig={state.getStatusConfig}
          getPriorityConfig={state.getPriorityConfig}
          onTicketSwitch={onTicketSwitch}
        />

        {/* Middle Panel - Conversation */}
        <TicketConversation
          ticket={ticket}
          handleCopyTicketId={state.handleCopyTicketId}
          snoozed={state.snoozed}
          isStarred={state.isStarred}
          handleToggleStar={state.handleToggleStar}
          showMoreMenu={state.showMoreMenu}
          setShowMoreMenu={state.setShowMoreMenu}
          handleCopyLink={state.handleCopyLink}
          handleOpenInNewTab={state.handleOpenInNewTab}
          handlePrint={state.handlePrint}
          handleToggleSnooze={state.handleToggleSnooze}
          handleAssignToMe={state.handleAssignToMe}
          setShowMergeModal={state.setShowMergeModal}
          setShowLinkModal={state.setShowLinkModal}
          setShowSplitModal={state.setShowSplitModal}
          setShowFeatureRequestModal={state.setShowFeatureRequestModal}
          setSplitMessageIndex={state.setSplitMessageIndex}
          setShowDeleteConfirm={state.setShowDeleteConfirm}
          handleCloseWithAnimation={state.handleCloseWithAnimation}
          activeTab={state.activeTab}
          setActiveTab={state.setActiveTab}
          conversationRef={state.conversationRef}
          activityFeed={state.activityFeed}
          loadingActivity={state.loadingActivity}
          mergeSuggestions={state.mergeSuggestions}
          dismissedMergeSuggestions={state.dismissedMergeSuggestions}
          setDismissedMergeSuggestions={state.setDismissedMergeSuggestions}
          handleAcceptMergeSuggestion={state.handleAcceptMergeSuggestion}
          mergedTickets={state.mergedTickets}
          showMergedPanel={state.showMergedPanel}
          setShowMergedPanel={state.setShowMergedPanel}
          handleUnmerge={state.handleUnmerge}
          messageSourceFilter={state.messageSourceFilter}
          setMessageSourceFilter={state.setMessageSourceFilter}
          conversationThread={state.conversationThread}
          loadingNotes={state.loadingNotes}
          handleSaveToKB={state.handleSaveToKB}
          othersTyping={state.othersTyping}
          inputMode={state.inputMode}
          setInputMode={state.setInputMode}
          showCannedPicker={state.showCannedPicker}
          setShowCannedPicker={state.setShowCannedPicker}
          showKBPicker={state.showKBPicker}
          setShowKBPicker={state.setShowKBPicker}
          imageInputRef={state.imageInputRef}
          uploadingImage={state.uploadingImage}
          attachedImages={state.attachedImages}
          inputText={state.inputText}
          setInputText={state.setInputText}
          setInputMentions={state.setInputMentions}
          handleTypingChange={state.handleTypingChange}
          handleSubmitInput={state.handleSubmitInput}
          submitting={state.submitting}
          handleCannedResponseSelect={state.handleCannedResponseSelect}
          handleImageUpload={state.handleImageUpload}
          removeAttachedImage={state.removeAttachedImage}
        />

        {/* Right Panel - Details */}
        <TicketDetailsPanel
          ticket={ticket}
          users={users}
          currentUser={currentUser}
          formData={state.formData}
          setFormData={state.setFormData}
          showDeleteConfirm={state.showDeleteConfirm}
          setShowDeleteConfirm={state.setShowDeleteConfirm}
          handleDelete={state.handleDelete}
          escalating={state.escalating}
          handleEscalate={state.handleEscalate}
          assignmentOptions={state.assignmentOptions}
          showAssignDropdown={state.showAssignDropdown}
          setShowAssignDropdown={state.setShowAssignDropdown}
          handleAssignToMe={state.handleAssignToMe}
          handleAssign={state.handleAssign}
          handleAssignToTeam={state.handleAssignToTeam}
          statusConfig={state.statusConfig}
          priorityConfig={state.priorityConfig}
          assignee={state.assignee}
          sectionsExpanded={state.sectionsExpanded}
          toggleSection={state.toggleSection}
          linkedFeatureRequests={state.linkedFeatureRequests}
          handleUnlinkFeatureRequest={state.handleUnlinkFeatureRequest}
          setShowFeatureRequestModal={state.setShowFeatureRequestModal}
          linkedTickets={state.linkedTickets}
          handleUnlinkTicket={state.handleUnlinkTicket}
          setShowLinkModal={state.setShowLinkModal}
          handleCopyLink={state.handleCopyLink}
          ticketTags={state.ticketTags}
          tagInput={state.tagInput}
          setTagInput={state.setTagInput}
          showTagDropdown={state.showTagDropdown}
          setShowTagDropdown={state.setShowTagDropdown}
          filteredTags={state.filteredTags}
          loadingTags={state.loadingTags}
          availableTags={state.availableTags}
          handleAddTag={state.handleAddTag}
          handleRemoveTag={state.handleRemoveTag}
          csatData={state.csatData}
          sendingCsat={state.sendingCsat}
          handleSendCsat={state.handleSendCsat}
          customFields={state.customFields}
          customFieldValues={state.customFieldValues}
          setCustomFieldValues={state.setCustomFieldValues}
        />
      </div>

      {/* Merge Ticket Modal */}
      {state.showMergeModal && (
        <MergeTicketModal
          ticket={ticket}
          onClose={() => state.setShowMergeModal(false)}
          onMerge={state.handleMerge}
        />
      )}

      {/* Link Ticket Modal */}
      {state.showLinkModal && (
        <LinkTicketModal
          ticket={ticket}
          linkedTickets={state.linkedTickets}
          onClose={() => state.setShowLinkModal(false)}
          onLink={state.handleLinkTicket}
          onUnlink={state.handleLinkModalUnlink}
        />
      )}

      {/* Split Ticket Modal */}
      {state.showSplitModal && (
        <SplitTicketModal
          ticket={ticket}
          notes={state.notes}
          splitMessageIndex={state.splitMessageIndex}
          onClose={() => state.setShowSplitModal(false)}
          onSplit={state.handleSplitTicket}
        />
      )}

      {/* Feature Request Modal */}
      {state.showFeatureRequestModal && (
        <FeatureRequestModal
          ticket={ticket}
          onClose={() => state.setShowFeatureRequestModal(false)}
          onLink={state.handleLinkFeatureRequest}
        />
      )}

      {/* Canned Response Picker Modal */}
      <CannedResponsePicker
        isOpen={state.showCannedPicker}
        onClose={() => state.setShowCannedPicker(false)}
        onSelect={state.handleCannedResponseSelect}
        ticket={ticket}
        user={currentUser}
      />

      {/* Knowledge Base Picker Modal */}
      <KnowledgeBasePicker
        isOpen={state.showKBPicker}
        onClose={() => state.setShowKBPicker(false)}
        onInsertLink={state.handleKBInsertLink}
        onInsertContent={state.handleKBInsertContent}
      />
    </>
  );
};

export default TicketDrawer;
