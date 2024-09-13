package com.renderer;

public class Main {
    public static void main(String[] args) {
        var renderer = new Renderer();
        var input = args[0];
        var output = renderer.render(input, null);
        System.out.print(output);
    }
}