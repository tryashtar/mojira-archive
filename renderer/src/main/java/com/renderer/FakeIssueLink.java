package com.renderer;

import java.text.ParseException;

import com.atlassian.jira.issue.IssueManager;
import com.atlassian.jira.issue.MutableIssue;
import com.atlassian.renderer.RenderContext;
import com.atlassian.renderer.links.Link;

public class FakeIssueLink extends Link {
   private String issueKey;
   private final IssueManager Manager;

   public FakeIssueLink(String issueKey, String linkTitle, IssueManager manager, RenderContext context) throws ParseException {
      super(issueKey);
      this.Manager = manager;
      this.setupIssueLink(issueKey, linkTitle, context);
   }

   private void setupIssueLink(String key, String linkTitle, RenderContext context) throws ParseException {
      MutableIssue issue;
      try {
         issue = Manager.getIssueObject(key);
         if (issue != null) {
            this.title = issue.getSummary();
            this.issueKey = issue.getKey();
            this.url = context.getBaseUrl() + "/browse/" + this.issueKey;
            if (issue.getResolution() != null) {
               this.linkBody = "-" + (linkTitle == null ? key : linkTitle) + "-";
            } else {
               this.linkBody = linkTitle == null ? key : linkTitle;
            }
         }
      } catch (Exception var5) {
         throw new IllegalArgumentException("No issue found with key " + key);
      }

      if (issue == null) {
         throw new ParseException("Unable to resolve the JIRA issue for key: " + key, 0);
      }
   }

   public String getLinkAttributes() {
      return String.format("%s class=\"issue-link\" data-issue-key=\"%s\"", super.getLinkAttributes(), this.issueKey);
   }
}
