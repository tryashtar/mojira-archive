package com.renderer;

import java.sql.Timestamp;
import java.util.Collection;
import java.util.Set;

import org.ofbiz.core.entity.GenericValue;

import com.atlassian.jira.bc.project.component.ProjectComponent;
import com.atlassian.jira.issue.Issue;
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

public class FakeIssue implements Issue {

   @Override
   public Long getLong(String arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getLong'");
   }

   @Override
   public String getString(String arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getString'");
   }

   @Override
   public Timestamp getTimestamp(String arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getTimestamp'");
   }

   @Override
   public void store() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'store'");
   }

   @Override
   public Collection<Version> getAffectedVersions() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getAffectedVersions'");
   }

   @Override
   public ApplicationUser getAssignee() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getAssignee'");
   }

   @Override
   public String getAssigneeId() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getAssigneeId'");
   }

   @Override
   public ApplicationUser getAssigneeUser() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getAssigneeUser'");
   }

   @Override
   public Collection<Attachment> getAttachments() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getAttachments'");
   }

   @Override
   public Collection<ProjectComponent> getComponentObjects() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getComponentObjects'");
   }

   @Override
   public Collection<ProjectComponent> getComponents() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getComponents'");
   }

   @Override
   public Timestamp getCreated() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getCreated'");
   }

   @Override
   public ApplicationUser getCreator() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getCreator'");
   }

   @Override
   public String getCreatorId() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getCreatorId'");
   }

   @Override
   public Object getCustomFieldValue(CustomField arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getCustomFieldValue'");
   }

   @Override
   public String getDescription() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getDescription'");
   }

   @Override
   public Timestamp getDueDate() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getDueDate'");
   }

   @Override
   public String getEnvironment() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getEnvironment'");
   }

   @Override
   public Long getEstimate() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getEstimate'");
   }

   @Override
   public Object getExternalFieldValue(String arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getExternalFieldValue'");
   }

   @Override
   public Collection<Version> getFixVersions() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getFixVersions'");
   }

   @Override
   public GenericValue getGenericValue() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getGenericValue'");
   }

   @Override
   public Long getId() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getId'");
   }

   @Override
   public IssueRenderContext getIssueRenderContext() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getIssueRenderContext'");
   }

   @Override
   public IssueType getIssueType() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getIssueType'");
   }

   @Override
   public String getIssueTypeId() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getIssueTypeId'");
   }

   @Override
   public IssueType getIssueTypeObject() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getIssueTypeObject'");
   }

   @Override
   public String getKey() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getKey'");
   }

   @Override
   public Set<Label> getLabels() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getLabels'");
   }

   @Override
   public Long getNumber() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getNumber'");
   }

   @Override
   public Long getOriginalEstimate() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getOriginalEstimate'");
   }

   @Override
   public GenericValue getParent() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getParent'");
   }

   @Override
   public Long getParentId() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getParentId'");
   }

   @Override
   public Issue getParentObject() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getParentObject'");
   }

   @Override
   public Priority getPriority() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getPriority'");
   }

   @Override
   public Priority getPriorityObject() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getPriorityObject'");
   }

   @Override
   public GenericValue getProject() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getProject'");
   }

   @Override
   public Long getProjectId() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getProjectId'");
   }

   @Override
   public Project getProjectObject() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getProjectObject'");
   }

   @Override
   public ApplicationUser getReporter() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getReporter'");
   }

   @Override
   public String getReporterId() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getReporterId'");
   }

   @Override
   public ApplicationUser getReporterUser() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getReporterUser'");
   }

   @Override
   public Resolution getResolution() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getResolution'");
   }

   @Override
   public Timestamp getResolutionDate() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getResolutionDate'");
   }

   @Override
   public String getResolutionId() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getResolutionId'");
   }

   @Override
   public Resolution getResolutionObject() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getResolutionObject'");
   }

   @Override
   public GenericValue getSecurityLevel() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getSecurityLevel'");
   }

   @Override
   public Long getSecurityLevelId() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getSecurityLevelId'");
   }

   @Override
   public Status getStatus() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getStatus'");
   }

   @Override
   public String getStatusId() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getStatusId'");
   }

   @Override
   public Status getStatusObject() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getStatusObject'");
   }

   @Override
   public Collection<Issue> getSubTaskObjects() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getSubTaskObjects'");
   }

   @Override
   public Collection<GenericValue> getSubTasks() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getSubTasks'");
   }

   @Override
   public String getSummary() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getSummary'");
   }

   @Override
   public Long getTimeSpent() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getTimeSpent'");
   }

   @Override
   public Timestamp getUpdated() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getUpdated'");
   }

   @Override
   public Long getVotes() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getVotes'");
   }

   @Override
   public Long getWatches() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getWatches'");
   }

   @Override
   public Long getWorkflowId() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getWorkflowId'");
   }

   @Override
   public boolean isCreated() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'isCreated'");
   }

   @Override
   public boolean isEditable() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'isEditable'");
   }

   @Override
   public boolean isSubTask() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'isSubTask'");
   }
   
}
