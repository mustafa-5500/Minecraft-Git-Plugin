package com.example.minecrafttemplateplugin;

import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.plugin.java.JavaPlugin;

public final class TemplatePlugin extends JavaPlugin {

    @Override
    public void onEnable() {
        getLogger().info("TemplatePlugin has been enabled.");
    }

    @Override
    public void onDisable() {
        getLogger().info("TemplatePlugin has been disabled.");
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (command.getName().equalsIgnoreCase("template")) {
            sender.sendMessage("Template plugin is working.");
            return true;
        }
        return false;
    }
}
