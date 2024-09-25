package com.renderer;

import java.sql.Timestamp;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.ofbiz.core.entity.GenericValue;
import org.ofbiz.core.entity.model.ModelEntity;

import com.atlassian.jira.bc.project.component.ProjectComponent;
import com.atlassian.jira.issue.Issue;
import com.atlassian.jira.issue.ModifiedValue;
import com.atlassian.jira.issue.MutableIssue;
import com.atlassian.jira.issue.attachment.Attachment;
import com.atlassian.jira.issue.fields.CustomField;
import com.atlassian.jira.issue.fields.renderer.IssueRenderContext;
import com.atlassian.jira.issue.issuetype.IssueType;
import com.atlassian.jira.issue.label.Label;
import com.atlassian.jira.issue.priority.Priority;
import com.atlassian.jira.issue.resolution.Resolution;
import com.atlassian.jira.issue.status.Status;
import com.atlassian.jira.project.Project;
import com.atlassian.jira.project.version.Version;
import com.atlassian.jira.user.ApplicationUser;

public class FakeIssue implements MutableIssue {
   private final long Id;
   private final String Key;
   private final String Resolution;
   private final String Summary;
   private final List<Attachment> Attachments;
   public FakeIssue(long id, String key, String resolution, String summary, List<Attachment> attachments) {
      this.Id = id;
      this.Key = key;
      this.Resolution = resolution;
      this.Summary = summary;
      this.Attachments = attachments;
   }

   public Long getId() {
      return this.Id;
   }

   public String getSummary() {
      return this.Summary;
   }

   public String getKey() {
      return this.Key;
   }

   public Resolution getResolution() {
      return this.Resolution == null ? null : new FakeResolution();
   }

   public GenericValue getGenericValue() {
      return new GenericValue(null, new ModelEntity());
   }

   public Collection<Attachment> getAttachments() {
      return this.Attachments;
   }

   public Collection<Version> getAffectedVersions() {
      throw new UnsupportedOperationException();
   }

   public ApplicationUser getAssignee() {
      throw new UnsupportedOperationException();
   }

   public String getAssigneeId() {
      throw new UnsupportedOperationException();
   }

   public ApplicationUser getAssigneeUser() {
      throw new UnsupportedOperationException();
   }

   public Collection<ProjectComponent> getComponentObjects() {
      throw new UnsupportedOperationException();
   }

   public Collection<ProjectComponent> getComponents() {
      throw new UnsupportedOperationException();
   }

   public Timestamp getCreated() {
      throw new UnsupportedOperationException();
   }

   public ApplicationUser getCreator() {
      throw new UnsupportedOperationException();
   }

   public String getCreatorId() {
      throw new UnsupportedOperationException();
   }

   public Object getCustomFieldValue(CustomField arg0) {
      throw new UnsupportedOperationException();
   }

   public String getDescription() {
      throw new UnsupportedOperationException();
   }

   public Timestamp getDueDate() {
      throw new UnsupportedOperationException();
   }

   public String getEnvironment() {
      throw new UnsupportedOperationException();
   }

   public Long getEstimate() {
      throw new UnsupportedOperationException();
   }

   public Object getExternalFieldValue(String arg0) {
      throw new UnsupportedOperationException();
   }

   public Collection<Version> getFixVersions() {
      throw new UnsupportedOperationException();
   }

   public IssueRenderContext getIssueRenderContext() {
      throw new UnsupportedOperationException();
   }

   public IssueType getIssueType() {
      throw new UnsupportedOperationException();
   }

   public String getIssueTypeId() {
      throw new UnsupportedOperationException();
   }

   public IssueType getIssueTypeObject() {
      throw new UnsupportedOperationException();
   }



   public Set<Label> getLabels() {
      throw new UnsupportedOperationException();
   }

   public Long getNumber() {
      throw new UnsupportedOperationException();
   }

   public Long getOriginalEstimate() {
      throw new UnsupportedOperationException();
   }

   public GenericValue getParent() {
      throw new UnsupportedOperationException();
   }

   public Long getParentId() {
      throw new UnsupportedOperationException();
   }

   public Issue getParentObject() {
      throw new UnsupportedOperationException();
   }

   public Priority getPriority() {
      throw new UnsupportedOperationException();
   }

   public Priority getPriorityObject() {
      throw new UnsupportedOperationException();
   }

   public GenericValue getProject() {
      throw new UnsupportedOperationException();
   }

   public Long getProjectId() {
      throw new UnsupportedOperationException();
   }

   public Project getProjectObject() {
      throw new UnsupportedOperationException();
   }

   public ApplicationUser getReporter() {
      throw new UnsupportedOperationException();
   }

   public String getReporterId() {
      throw new UnsupportedOperationException();
   }

   public ApplicationUser getReporterUser() {
      throw new UnsupportedOperationException();
   }

   public Resolution getResolutionObject() {
      throw new UnsupportedOperationException();
   }

   public Timestamp getResolutionDate() {
      throw new UnsupportedOperationException();
   }

   public String getResolutionId() {
      throw new UnsupportedOperationException();
   }

   public GenericValue getSecurityLevel() {
      throw new UnsupportedOperationException();
   }

   public Long getSecurityLevelId() {
      throw new UnsupportedOperationException();
   }

   public Status getStatus() {
      throw new UnsupportedOperationException();
   }

   public String getStatusId() {
      throw new UnsupportedOperationException();
   }

   public Status getStatusObject() {
      throw new UnsupportedOperationException();
   }

   public Collection<Issue> getSubTaskObjects() {
      throw new UnsupportedOperationException();
   }

   public Collection<GenericValue> getSubTasks() {
      throw new UnsupportedOperationException();
   }

   public Long getTimeSpent() {
      throw new UnsupportedOperationException();
   }

   public Timestamp getUpdated() {
      throw new UnsupportedOperationException();
   }

   public Long getVotes() {
      throw new UnsupportedOperationException();
   }

   public Long getWatches() {
      throw new UnsupportedOperationException();
   }

   public Long getWorkflowId() {
      throw new UnsupportedOperationException();
   }

   public boolean isCreated() {
      throw new UnsupportedOperationException();
   }

   public boolean isEditable() {
      throw new UnsupportedOperationException();
   }

   public boolean isSubTask() {
      throw new UnsupportedOperationException();
   }

   public Long getLong(String arg0) {
      throw new UnsupportedOperationException();
   }

   public String getString(String arg0) {
      throw new UnsupportedOperationException();
   }

   public Timestamp getTimestamp(String arg0) {
      throw new UnsupportedOperationException();
   }

   @SuppressWarnings("rawtypes")
   public Map<String, ModifiedValue> getModifiedFields() {
      throw new UnsupportedOperationException();
   }

   public void resetModifiedFields() {
      throw new UnsupportedOperationException();
   }

   public void setAffectedVersions(Collection<Version> arg0) {
      throw new UnsupportedOperationException();
   }

   public void setAssignee(ApplicationUser arg0) {
      throw new UnsupportedOperationException();
   }

   public void setAssigneeId(String arg0) {
      throw new UnsupportedOperationException();
   }

   public void setComponent(Collection<ProjectComponent> arg0) {
      throw new UnsupportedOperationException();
   }

   public void setCreated(Timestamp arg0) {
      throw new UnsupportedOperationException();
   }

   public void setCustomFieldValue(CustomField arg0, Object arg1) {
      throw new UnsupportedOperationException();
   }

   public void setDescription(String arg0) {
      throw new UnsupportedOperationException();
   }

   public void setDueDate(Timestamp arg0) {
      throw new UnsupportedOperationException();
   }

   public void setEnvironment(String arg0) {
      throw new UnsupportedOperationException();
   }

   public void setEstimate(Long arg0) {
      throw new UnsupportedOperationException();
   }

   public void setExternalFieldValue(String arg0, Object arg1) {
      throw new UnsupportedOperationException();
   }

   public void setExternalFieldValue(String arg0, Object arg1, Object arg2) {
      throw new UnsupportedOperationException();
   }

   public void setFixVersions(Collection<Version> arg0) {
      throw new UnsupportedOperationException();
   }

   public void setIssueType(IssueType arg0) {
      throw new UnsupportedOperationException();
   }

   public void setIssueTypeId(String arg0) {
      throw new UnsupportedOperationException();
   }

   public void setIssueTypeObject(IssueType arg0) {
      throw new UnsupportedOperationException();
   }

   public void setKey(String arg0) {
      throw new UnsupportedOperationException();
   }

   public void setLabels(Set<Label> arg0) {
      throw new UnsupportedOperationException();
   }

   public void setNumber(Long arg0) {
      throw new UnsupportedOperationException();
   }

   public void setOriginalEstimate(Long arg0) {
      throw new UnsupportedOperationException();
   }

   public void setParentId(Long arg0) {
      throw new UnsupportedOperationException();
   }

   public void setParentObject(Issue arg0) {
      throw new UnsupportedOperationException();
   }

   public void setPriority(Priority arg0) {
      throw new UnsupportedOperationException();
   }

   public void setPriorityId(String arg0) {
      throw new UnsupportedOperationException();
   }

   public void setPriorityObject(Priority arg0) {
      throw new UnsupportedOperationException();
   }

   public void setProject(GenericValue arg0) {
      throw new UnsupportedOperationException();
   }

   public void setProjectId(Long arg0) throws IllegalArgumentException {
      throw new UnsupportedOperationException();
   }

   public void setProjectObject(Project arg0) {
      throw new UnsupportedOperationException();
   }

   public void setReporter(ApplicationUser arg0) {
      throw new UnsupportedOperationException();
   }

   public void setReporterId(String arg0) {
      throw new UnsupportedOperationException();
   }

   public void setResolution(Resolution arg0) {
      throw new UnsupportedOperationException();
   }

   public void setResolutionDate(Timestamp arg0) {
      throw new UnsupportedOperationException();
   }

   public void setResolutionId(String arg0) {
      throw new UnsupportedOperationException();
   }

   public void setResolutionObject(Resolution arg0) {
      throw new UnsupportedOperationException();
   }

   public void setSecurityLevel(GenericValue arg0) {
      throw new UnsupportedOperationException();
   }

   public void setSecurityLevelId(Long arg0) {
      throw new UnsupportedOperationException();
   }

   public void setStatus(Status arg0) {
      throw new UnsupportedOperationException();
   }

   public void setStatusId(String arg0) {
      throw new UnsupportedOperationException();
   }

   public void setStatusObject(Status arg0) {
      throw new UnsupportedOperationException();
   }

   public void setSummary(String arg0) {
      throw new UnsupportedOperationException();
   }

   public void setTimeSpent(Long arg0) {
      throw new UnsupportedOperationException();
   }

   public void setUpdated(Timestamp arg0) {
      throw new UnsupportedOperationException();
   }

   public void setVotes(Long arg0) {
      throw new UnsupportedOperationException();
   }

   public void setWatches(Long arg0) {
      throw new UnsupportedOperationException();
   }

   public void setWorkflowId(Long arg0) {
      throw new UnsupportedOperationException();
   }

   public void store() {
      throw new UnsupportedOperationException();
   }

   public String getArchivedById() {
      throw new UnsupportedOperationException();
   }

   public ApplicationUser getArchivedByUser() {
      throw new UnsupportedOperationException();
   }

   public Timestamp getArchivedDate() {
      throw new UnsupportedOperationException();
   }

   public boolean isArchived() {
      throw new UnsupportedOperationException();
   }

   public void setArchived(boolean arg0) {
      throw new UnsupportedOperationException();
   }   
}
