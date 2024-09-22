package com.renderer;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
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
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

public class FakeIssueManager implements IssueManager {
   private final Path issueFolder;
   private JsonObject keyMap = null;

   public FakeIssueManager(Path issueFolder) {
      this.issueFolder = issueFolder;
   }

   public void setKeyMap(JsonObject keyMap) {
      this.keyMap = keyMap;
   }

   public MutableIssue getIssueObject(String key) throws DataAccessException {
      var id = this.keyMap.get(key).getAsLong();
      return this.getIssueObject(id);
   }

   public MutableIssue getIssueObject(Long id) throws DataAccessException {
      var path = issueFolder.resolve(id.toString() + ".json");
      String json;
      try {
         json = Files.readString(path);
      } catch (IOException ex) {
         return null;
      }
      var data = new JsonParser().parse(json).getAsJsonObject();
      var key = data.get("key").getAsString();
      var fields = data.get("fields").getAsJsonObject();
      var resolutionField = fields.get("resolution");
      var resolution = resolutionField.isJsonNull() ? null : resolutionField.getAsString();
      var summary = fields.get("summary").getAsString();
      return new FakeIssue(id, key, resolution, summary);
   }

   public boolean atLeastOneIssueExists() {
      throw new UnsupportedOperationException();
   }

   public GenericValue createIssue(String arg0, Map<String, Object> arg1) throws CreateException {
      throw new UnsupportedOperationException();
   }

   public GenericValue createIssue(ApplicationUser arg0, Map<String, Object> arg1) throws CreateException {
      throw new UnsupportedOperationException();
   }

   public GenericValue createIssue(ApplicationUser arg0, Issue arg1) throws CreateException {
      throw new UnsupportedOperationException();
   }

   public Issue createIssueObject(String arg0, Map<String, Object> arg1) throws CreateException {
      throw new UnsupportedOperationException();
   }

   public Issue createIssueObject(ApplicationUser arg0, Map<String, Object> arg1) throws CreateException {
      throw new UnsupportedOperationException();
   }

   public Issue createIssueObject(ApplicationUser arg0, Issue arg1) throws CreateException {
      throw new UnsupportedOperationException();
   }

   public void deleteIssue(ApplicationUser arg0, Issue arg1, EventDispatchOption arg2, boolean arg3)
         throws RemoveException {
      throw new UnsupportedOperationException();
   }

   public void deleteIssue(ApplicationUser arg0, MutableIssue arg1, EventDispatchOption arg2, boolean arg3)
         throws RemoveException {
      throw new UnsupportedOperationException();
   }

   public void deleteIssueNoEvent(Issue arg0) throws RemoveException {
      throw new UnsupportedOperationException();
   }

   public void deleteIssueNoEvent(MutableIssue arg0) throws RemoveException {
      throw new UnsupportedOperationException();
   }

   public Issue findMovedIssue(String arg0) {
      throw new UnsupportedOperationException();
   }

   public Set<String> getAllIssueKeys(Long arg0) {
      throw new UnsupportedOperationException();
   }

   public List<GenericValue> getEntitiesByIssue(String arg0, GenericValue arg1) throws GenericEntityException {
      throw new UnsupportedOperationException();
   }

   public List<GenericValue> getEntitiesByIssueObject(String arg0, Issue arg1) throws GenericEntityException {
      throw new UnsupportedOperationException();
   }

   public Set<Long> getIdsOfMissingIssues(Set<Long> arg0) {
      throw new UnsupportedOperationException();
   }

   public GenericValue getIssue(Long arg0) throws DataAccessException {
      throw new UnsupportedOperationException();
   }

   public GenericValue getIssue(String arg0) throws GenericEntityException {
      throw new UnsupportedOperationException();
   }

   public MutableIssue getIssueByCurrentKey(String arg0) throws DataAccessException {
      throw new UnsupportedOperationException();
   }

   public MutableIssue getIssueByKeyIgnoreCase(String arg0) throws DataAccessException {
      throw new UnsupportedOperationException();
   }

   public GenericValue getIssueByWorkflow(Long arg0) throws GenericEntityException {
      throw new UnsupportedOperationException();
   }

   public long getIssueCount() {
      throw new UnsupportedOperationException();
   }

   public long getIssueCountForProject(Long arg0) {
      throw new UnsupportedOperationException();
   }

   public Collection<Long> getIssueIdsForProject(Long arg0) throws GenericEntityException {
      throw new UnsupportedOperationException();
   }

   public MutableIssue getIssueObjectByWorkflow(Long arg0) throws GenericEntityException {
      throw new UnsupportedOperationException();
   }

   public List<Issue> getIssueObjects(Collection<Long> arg0) {
      throw new UnsupportedOperationException();
   }

   public List<Issue> getIssueObjectsByEntity(String arg0, GenericValue arg1) throws GenericEntityException {
      throw new UnsupportedOperationException();
   }

   public List<GenericValue> getIssues(Collection<Long> arg0) {
      throw new UnsupportedOperationException();
   }

   public List<GenericValue> getIssuesByEntity(String arg0, GenericValue arg1) throws GenericEntityException {
      throw new UnsupportedOperationException();
   }

   public Set<String> getKeysOfMissingIssues(Set<String> arg0) {
      throw new UnsupportedOperationException();
   }

   public Set<Pair<Long, String>> getProjectIssueTypePairsByIds(Set<Long> arg0) {
      throw new UnsupportedOperationException();
   }

   public Set<Pair<Long, String>> getProjectIssueTypePairsByKeys(Set<String> arg0) {
      throw new UnsupportedOperationException();
   }

   public List<GenericValue> getProjectIssues(GenericValue arg0) throws GenericEntityException {
      throw new UnsupportedOperationException();
   }

   public long getUnassignedIssueCount() {
      throw new UnsupportedOperationException();
   }

   public List<Issue> getVotedIssues(ApplicationUser arg0) {
      throw new UnsupportedOperationException();
   }

   public List<Issue> getVotedIssuesOverrideSecurity(ApplicationUser arg0) {
      throw new UnsupportedOperationException();
   }

   public List<Issue> getWatchedIssues(ApplicationUser arg0) {
      throw new UnsupportedOperationException();
   }

   public List<Issue> getWatchedIssuesOverrideSecurity(ApplicationUser arg0) {
      throw new UnsupportedOperationException();
   }

   public List<ApplicationUser> getWatchers(Issue arg0) {
      throw new UnsupportedOperationException();
   }

   public List<ApplicationUser> getWatchersFor(Issue arg0) {
      throw new UnsupportedOperationException();
   }

   public boolean hasUnassignedIssues() {
      throw new UnsupportedOperationException();
   }

   public boolean isEditable(Issue arg0) {
      throw new UnsupportedOperationException();
   }

   public boolean isEditable(Issue arg0, ApplicationUser arg1) {
      throw new UnsupportedOperationException();
   }

   public boolean isExistingIssueKey(String arg0) throws GenericEntityException {
      throw new UnsupportedOperationException();
   }

   public void recordMovedIssueKey(Issue arg0) {
      throw new UnsupportedOperationException();
   }

   public Issue updateIssue(ApplicationUser arg0, MutableIssue arg1, UpdateIssueRequest arg2) {
      throw new UnsupportedOperationException();
   }

   public Issue updateIssue(ApplicationUser arg0, MutableIssue arg1, EventDispatchOption arg2, boolean arg3) {
      throw new UnsupportedOperationException();
   }
}
