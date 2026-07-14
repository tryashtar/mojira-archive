package com.renderer;

import java.io.UnsupportedEncodingException;

import com.atlassian.jira.user.ApplicationUser;
import com.atlassian.jira.user.util.UserManager;
import com.atlassian.jira.util.URLCodec;
import com.atlassian.renderer.RenderContext;
import com.atlassian.renderer.links.BaseLink;
import com.atlassian.renderer.links.GenericLinkParser;
import com.opensymphony.util.TextUtils;

public class FakeUserProfileLink extends BaseLink {
    private ApplicationUser user;

    public FakeUserProfileLink(GenericLinkParser parser, RenderContext context, UserManager manager) {
        super(parser);
        if (TextUtils.stringSet(parser.getNotLinkBody()) && parser.getNotLinkBody().startsWith("~")) {
            try {
                String username = parser.getNotLinkBody().substring(1);
                this.user = manager.getUserByName(username);
                if (this.user != null && this.user.getDisplayName() != null) {
                    this.linkBody = this.user.getDisplayName();
                } else {
                    this.linkBody = username;
                }

                this.url = this.buildProfileUrl(context, username);
            } catch (Exception var4) {
            }
        }
    }

    public String getLinkAttributes() {
        return this.user != null
                ? super.getLinkAttributes() + " class=\"user-hover\" rel=\"" + TextUtils.htmlEncode(this.user.getName())
                + "\""
                : super.getLinkAttributes();
    }

    private String buildProfileUrl(RenderContext context, String username) throws UnsupportedEncodingException {
        String encodedUsername = URLCodec.encode(username, context.getCharacterEncoding());
        return context.getBaseUrl() + "/secure/ViewProfile.jspa?name=" + encodedUsername;
    }

    public ApplicationUser getUser() {
        return this.user;
    }
}
