package com.renderer;

import com.atlassian.jira.issue.fields.renderer.IssueRenderContext;

public class Main {
    public static void main(String[] args) {
        var renderer = new FakeRenderer();
        var input = args[0];
        var context = new IssueRenderContext(new FakeIssue());
        var output = renderer.render(input, context);
        System.out.print(output);
    }
}