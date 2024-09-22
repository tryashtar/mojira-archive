package com.renderer;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.ofbiz.core.entity.GenericEntityException;
import org.ofbiz.core.entity.GenericValue;

import com.atlassian.jira.event.type.EventDispatchOption;
import com.atlassian.jira.exception.CreateException;
import com.atlassian.jira.exception.DataAccessException;
import com.atlassian.jira.exception.RemoveException;
import com.atlassian.jira.issue.Issue;
import com.atlassian.jira.issue.IssueManager;
import com.atlassian.jira.issue.MutableIssue;
import com.atlassian.jira.issue.UpdateIssueRequest;
import com.atlassian.jira.user.ApplicationUser;
import com.atlassian.jira.util.lang.Pair;

public class FakeIssueManager implements IssueManager {

   @Override
   public boolean atLeastOneIssueExists() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'atLeastOneIssueExists'");
   }

   @Override
   public GenericValue createIssue(String arg0, Map<String, Object> arg1) throws CreateException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'createIssue'");
   }

   @Override
   public GenericValue createIssue(ApplicationUser arg0, Map<String, Object> arg1) throws CreateException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'createIssue'");
   }

   @Override
   public GenericValue createIssue(ApplicationUser arg0, Issue arg1) throws CreateException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'createIssue'");
   }

   @Override
   public Issue createIssueObject(String arg0, Map<String, Object> arg1) throws CreateException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'createIssueObject'");
   }

   @Override
   public Issue createIssueObject(ApplicationUser arg0, Map<String, Object> arg1) throws CreateException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'createIssueObject'");
   }

   @Override
   public Issue createIssueObject(ApplicationUser arg0, Issue arg1) throws CreateException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'createIssueObject'");
   }

   @Override
   public void deleteIssue(ApplicationUser arg0, Issue arg1, EventDispatchOption arg2, boolean arg3)
         throws RemoveException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'deleteIssue'");
   }

   @Override
   public void deleteIssue(ApplicationUser arg0, MutableIssue arg1, EventDispatchOption arg2, boolean arg3)
         throws RemoveException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'deleteIssue'");
   }

   @Override
   public void deleteIssueNoEvent(Issue arg0) throws RemoveException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'deleteIssueNoEvent'");
   }

   @Override
   public void deleteIssueNoEvent(MutableIssue arg0) throws RemoveException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'deleteIssueNoEvent'");
   }

   @Override
   public Issue findMovedIssue(String arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'findMovedIssue'");
   }

   @Override
   public Set<String> getAllIssueKeys(Long arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getAllIssueKeys'");
   }

   @Override
   public List<GenericValue> getEntitiesByIssue(String arg0, GenericValue arg1) throws GenericEntityException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getEntitiesByIssue'");
   }

   @Override
   public List<GenericValue> getEntitiesByIssueObject(String arg0, Issue arg1) throws GenericEntityException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getEntitiesByIssueObject'");
   }

   @Override
   public Set<Long> getIdsOfMissingIssues(Set<Long> arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getIdsOfMissingIssues'");
   }

   @Override
   public GenericValue getIssue(Long arg0) throws DataAccessException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getIssue'");
   }

   @Override
   public GenericValue getIssue(String arg0) throws GenericEntityException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getIssue'");
   }

   @Override
   public MutableIssue getIssueByCurrentKey(String arg0) throws DataAccessException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getIssueByCurrentKey'");
   }

   @Override
   public MutableIssue getIssueByKeyIgnoreCase(String arg0) throws DataAccessException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getIssueByKeyIgnoreCase'");
   }

   @Override
   public GenericValue getIssueByWorkflow(Long arg0) throws GenericEntityException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getIssueByWorkflow'");
   }

   @Override
   public long getIssueCount() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getIssueCount'");
   }

   @Override
   public long getIssueCountForProject(Long arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getIssueCountForProject'");
   }

   @Override
   public Collection<Long> getIssueIdsForProject(Long arg0) throws GenericEntityException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getIssueIdsForProject'");
   }

   @Override
   public MutableIssue getIssueObject(Long arg0) throws DataAccessException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getIssueObject'");
   }

   @Override
   public MutableIssue getIssueObject(String arg0) throws DataAccessException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getIssueObject'");
   }

   @Override
   public MutableIssue getIssueObjectByWorkflow(Long arg0) throws GenericEntityException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getIssueObjectByWorkflow'");
   }

   @Override
   public List<Issue> getIssueObjects(Collection<Long> arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getIssueObjects'");
   }

   @Override
   public List<Issue> getIssueObjectsByEntity(String arg0, GenericValue arg1) throws GenericEntityException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getIssueObjectsByEntity'");
   }

   @Override
   public List<GenericValue> getIssues(Collection<Long> arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getIssues'");
   }

   @Override
   public List<GenericValue> getIssuesByEntity(String arg0, GenericValue arg1) throws GenericEntityException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getIssuesByEntity'");
   }

   @Override
   public Set<String> getKeysOfMissingIssues(Set<String> arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getKeysOfMissingIssues'");
   }

   @Override
   public Set<Pair<Long, String>> getProjectIssueTypePairsByIds(Set<Long> arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getProjectIssueTypePairsByIds'");
   }

   @Override
   public Set<Pair<Long, String>> getProjectIssueTypePairsByKeys(Set<String> arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getProjectIssueTypePairsByKeys'");
   }

   @Override
   public List<GenericValue> getProjectIssues(GenericValue arg0) throws GenericEntityException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getProjectIssues'");
   }

   @Override
   public long getUnassignedIssueCount() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getUnassignedIssueCount'");
   }

   @Override
   public List<Issue> getVotedIssues(ApplicationUser arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getVotedIssues'");
   }

   @Override
   public List<Issue> getVotedIssuesOverrideSecurity(ApplicationUser arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getVotedIssuesOverrideSecurity'");
   }

   @Override
   public List<Issue> getWatchedIssues(ApplicationUser arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getWatchedIssues'");
   }

   @Override
   public List<Issue> getWatchedIssuesOverrideSecurity(ApplicationUser arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getWatchedIssuesOverrideSecurity'");
   }

   @Override
   public List<ApplicationUser> getWatchers(Issue arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getWatchers'");
   }

   @Override
   public List<ApplicationUser> getWatchersFor(Issue arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getWatchersFor'");
   }

   @Override
   public boolean hasUnassignedIssues() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'hasUnassignedIssues'");
   }

   @Override
   public boolean isEditable(Issue arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'isEditable'");
   }

   @Override
   public boolean isEditable(Issue arg0, ApplicationUser arg1) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'isEditable'");
   }

   @Override
   public boolean isExistingIssueKey(String arg0) throws GenericEntityException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'isExistingIssueKey'");
   }

   @Override
   public void recordMovedIssueKey(Issue arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'recordMovedIssueKey'");
   }

   @Override
   public Issue updateIssue(ApplicationUser arg0, MutableIssue arg1, UpdateIssueRequest arg2) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'updateIssue'");
   }

   @Override
   public Issue updateIssue(ApplicationUser arg0, MutableIssue arg1, EventDispatchOption arg2, boolean arg3) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'updateIssue'");
   }
   
}
