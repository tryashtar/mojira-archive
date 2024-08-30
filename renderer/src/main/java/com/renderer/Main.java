package com.renderer;

public class Main {
    public static void main(String[] args) {
        var input = args[0];
        var renderer = new Renderer();
        var output = renderer.plain2html(input);
        System.out.print(output);
    }
}