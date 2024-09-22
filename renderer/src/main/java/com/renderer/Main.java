package com.renderer;

import java.util.Scanner;

import com.atlassian.renderer.RenderContext;
import com.atlassian.renderer.RendererConfiguration;
import com.atlassian.renderer.embedded.DefaultEmbeddedResourceRenderer;
import com.atlassian.renderer.embedded.EmbeddedResourceRenderer;
import com.atlassian.renderer.links.LinkRenderer;
import com.atlassian.renderer.v2.RenderMode;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

public class Main {
    public static void main(String[] args) {
        var matcher = new FakeKeyMatcher();
        var manager = new FakeIssueManager();
        var resolver = new FakeLinkResolver(matcher, manager);
        var config = new FakeRendererConfiguration();
        var component = new FakeIssueLinkRendererComponent(matcher);
        var attachments = new FakeAttachmentManager();
        var renderer = new FakeRenderer(resolver, config, component);
        var embedded = new DefaultEmbeddedResourceRenderer(attachments);
        var input = new Scanner(System.in);
        var parser = new JsonParser();
        while (input.hasNext()) {
            var json_in = parser.parse(input.nextLine()).getAsJsonObject();
            var markup = json_in.get("markup").getAsString();
            var rendered = renderer.render(markup, makeRenderContext(renderer.LinkRenderer, embedded, config));
            var json_out = new JsonObject();
            json_out.addProperty("rendered", rendered);
            System.out.println(json_out.toString());
            System.out.flush();
        }
        input.close();
    }

    private static RenderContext makeRenderContext(LinkRenderer linkRenderer,
            EmbeddedResourceRenderer resourceRenderer, RendererConfiguration config) {
        var context = new RenderContext();
        context.setSiteRoot("");
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