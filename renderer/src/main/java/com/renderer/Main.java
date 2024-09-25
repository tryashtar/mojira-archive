package com.renderer;

import java.nio.file.Path;
import java.util.Scanner;

import org.apache.log4j.Level;
import org.apache.log4j.Logger;

import com.atlassian.jira.issue.Issue;
import com.atlassian.jira.issue.fields.renderer.wiki.JiraIconManager;
import com.atlassian.renderer.RenderContext;
import com.atlassian.renderer.RendererConfiguration;
import com.atlassian.renderer.embedded.EmbeddedResourceRenderer;
import com.atlassian.renderer.links.LinkRenderer;
import com.atlassian.renderer.v2.RenderMode;
import com.atlassian.renderer.v2.V2LinkRenderer;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

public class Main {
    public static void main(String[] args) {
        Logger.getRootLogger().setLevel(Level.OFF);
        var configuration = JsonParser.parseString(args[0]).getAsJsonObject();
        var issueManager = new FakeIssueManager(Path.of(configuration.get("issues").getAsString()));
        var userManager = new FakeUserManager(Path.of(configuration.get("users").getAsString()));
        var attachments = new FakeAttachmentManager(Path.of(configuration.get("attachments").getAsString()));
        var icons = new JiraIconManager();
        var matcher = new FakeKeyMatcher();
        var config = new FakeRendererConfiguration();
        var resolver = new FakeLinkResolver(matcher, issueManager, userManager);
        var component = new FakeIssueLinkRendererComponent(matcher, issueManager);
        var embedded = new FakeEmbeddedResourceRenderer(attachments);
        var renderer = new FakeRenderer(resolver, config, component, icons);
        var link_renderer = new V2LinkRenderer(renderer.SubRenderer, icons, config);

        var input = new Scanner(System.in);
        while (input.hasNext()) {
            var json_in = JsonParser.parseString(input.nextLine()).getAsJsonObject();
            var type = json_in.get("type").getAsString();
            if (type.equals("configure")) {
                var issueMap = json_in.get("issue_map").getAsJsonObject();
                var attachMap = json_in.get("attachment_map").getAsJsonObject();
                issueManager.setKeyMap(issueMap);
                attachments.setAttachmentMap(attachMap);
            } else if (type.equals("render")) {
                var markup = json_in.get("markup").getAsString();
                var issue_id = json_in.get("issue");
                var ticket = issue_id.isJsonNull() ? null : issueManager.getIssueObject(issue_id.getAsLong());
                var context = makeRenderContext(ticket, link_renderer, embedded, config);
                var rendered = renderer.render(markup, context);
                var json_out = new JsonObject();
                json_out.addProperty("rendered", rendered);
                System.out.println(json_out.toString());
                System.out.flush();
            }
        }
        input.close();
    }

    private static RenderContext makeRenderContext(Issue issue, LinkRenderer linkRenderer,
            EmbeddedResourceRenderer resourceRenderer, RendererConfiguration config) {
        var context = new RenderContext();
        context.addParam("jira.issue", issue);
        context.setSiteRoot("https://bugs.mojang.com");
        context.setImagePath(context.getSiteRoot() + "/images");
        context.setLinkRenderer(linkRenderer);
        context.setEmbeddedResourceRenderer(resourceRenderer);
        context.setCharacterEncoding(config.getCharacterEncoding());
        context.setBaseUrl("https://bugs.mojang.com");
        context.pushRenderMode(RenderMode.ALL_WITH_NO_MACRO_ERRORS);
        context.addParam("com.atlassian.renderer.v2.components.macro.render.consider.variable.format", true);
        return context;
    }
}