package com.renderer;

import org.apache.oro.text.perl.Perl5Util;

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

    public boolean isKeyInString(String s) {
        return this.perlUtil.match(this.getIssueKeyRegex(), s);
    }

    public String getProjectKeyRegex() {
        return this.projectKeyRegex;
    }

    public String getIssueKeyRegex() {
        return this.issueKeyRegex;
    }

    public boolean isValidIssueKey(String issueKey) {
        if (issueKey == null) {
            return false;
        }
        int hyphenLocation = issueKey.lastIndexOf(45);
        if (hyphenLocation > 0) {
            String projectKey = issueKey.substring(0, hyphenLocation);
            String issueNumber = issueKey.substring(hyphenLocation + 1);
            if (isValidProjectKey(projectKey)) {
                if (issueNumber.length() == 0) {
                    return false;
                }
                char[] chars = issueNumber.toCharArray();
                for (char c : chars) {
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

    public boolean isValidProjectKey(String projectKey) {
        if (StringUtils.isBlank((CharSequence) projectKey)) {
            return false;
        }
        return this.perlUtil.match(this.getProjectKeyRegex(), projectKey);
    }

    public boolean isIgnoreUrlWithKey() {
        return true;
    }

    public boolean isKeyDetectionBackwardsCompatible() {
        return false;
    }

    public String getLink(String key) {
        return key;
    }
}
