package com.renderer;

import org.apache.oro.text.perl.Perl5Util;

import com.atlassian.jira.util.JiraKeyUtils;
import com.atlassian.jira.util.JiraKeyUtils.KeyMatcher;

import org.apache.commons.lang3.StringUtils;

public class FakeKeyMatcher implements KeyMatcher {
      private final Perl5Util perlUtil = new Perl5Util();
      private final String projectKeyRegex;
      private final String issueKeyRegex;

      public FakeKeyMatcher() {
         this.projectKeyRegex = "/^[A-Z][A-Z]+$/";
         this.issueKeyRegex = "/(^|[^a-zA-Z]|\n)([A-Z][A-Z]+-[0-9]+)/";
      }

      @Override
      public boolean isKeyInString(String s) {
         return this.perlUtil.match(this.getIssueKeyRegex(), s);
      }

      @Override
      public String getProjectKeyRegex() {
         return this.projectKeyRegex;
      }

      @Override
      public String getIssueKeyRegex() {
         return this.issueKeyRegex;
      }

      @Override
      public boolean isValidIssueKey(String issueKey) {
         if (issueKey == null) {
            return false;
         }
         int hyphenLocation = issueKey.lastIndexOf(45);
         if (hyphenLocation > 0) {
            String projectKey = issueKey.substring(0, hyphenLocation);
            String issueNumber = issueKey.substring(hyphenLocation + 1);
            if (JiraKeyUtils.validProjectKey(projectKey)) {
               char[] chars;
               if (issueNumber.length() == 0) {
                  return false;
               }
               for (char c : chars = issueNumber.toCharArray()) {
                  if (Character.isDigit(c))
                     continue;
                  return false;
               }
               return true;
            }
            return false;
         }
         return false;
      }

      @Override
      public boolean isValidProjectKey(String projectKey) {
         if (StringUtils.isBlank((CharSequence) projectKey)) {
            return false;
         }
         return this.perlUtil.match(this.getProjectKeyRegex(), projectKey);
      }

      @Override
      public boolean isIgnoreUrlWithKey() {
         return true;
      }

      @Override
      public boolean isKeyDetectionBackwardsCompatible() {
         return false;
      }

      @Override
      public String getLink(String key) {
         return key;
      }

      //@Override
      //public String getLink(String key) {
      //   StringBuilder buff = new StringBuilder();
      //   try {
      //      MutableIssue issue = this.getIssueManager().getIssueObject(key);
      //      if (issue != null && this.canCurrentUserSeeIssue(issue)) {
      //         String title = TextUtils.htmlEncode((String) issue.getSummary());
      //         VelocityRequestContext velocityRequestContext = ComponentAccessor
      //               .getComponent(VelocityRequestContextFactory.class).getJiraVelocityRequestContext();
      //         buff.append("<a href=\"").append(velocityRequestContext.getBaseUrl()).append("/browse/")
      //               .append(issue.getKey()).append("\" title=\"").append(title).append("\"")
      //               .append(" class=\"issue-link\" data-issue-key=\"").append(issue.getKey()).append("\">");
      //         if (issue.getResolutionObject() != null) {
      //            buff.append("<strike>");
      //            buff.append(key);
      //            buff.append("</strike>");
      //         } else {
      //            buff.append(key);
      //         }
      //         buff.append("</a>");
      //      } else {
      //         buff.append(key);
      //      }
      //   } catch (Exception e) {
      //      buff.append(key);
      //   }
      //   return buff.toString();
      //}
   }
