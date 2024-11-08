package com.renderer;

import com.atlassian.crowd.embedded.api.User;
import com.atlassian.jira.user.ApplicationUser;

public class FakeUser implements ApplicationUser {
    private final String name;
    private final String displayName;

    public FakeUser(String name, String displayName) {
        this.name = name;
        this.displayName = displayName;
    }

    public String getName() {
        return name;
    }

    public String getDisplayName() {
        return displayName;
    }

    public Long getId() {
        throw new UnsupportedOperationException();
    }

    public long getDirectoryId() {
        throw new UnsupportedOperationException();
    }

    public User getDirectoryUser() {
        throw new UnsupportedOperationException();
    }

    public String getEmailAddress() {
        throw new UnsupportedOperationException();
    }

    public String getKey() {
        throw new UnsupportedOperationException();
    }

    public String getUsername() {
        throw new UnsupportedOperationException();
    }

    public boolean isActive() {
        throw new UnsupportedOperationException();
    }

}
