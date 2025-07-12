/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";

class TwitterOAuthComponent extends Component {
    setup() {
        this.state = useState({
            isAuthenticating: false,
            authUrl: null,
        });
    }

    async startAuthentication(accountId) {
        this.state.isAuthenticating = true;
        
        try {
            const result = await this.env.services.rpc("/twitter/api/test", {
                service_id: accountId,
            });
            
            if (result.auth_url) {
                this.state.authUrl = result.auth_url;
                // Open authentication URL in new window
                window.open(result.auth_url, '_blank', 'width=600,height=400');
            }
            
        } catch (error) {
            console.error("Authentication error:", error);
            this.env.services.notification.add(
                "Authentication failed: " + error.message,
                { type: "danger" }
            );
        } finally {
            this.state.isAuthenticating = false;
        }
    }

    async testConnection(serviceId) {
        try {
            const result = await this.env.services.rpc("/twitter/api/test", {
                service_id: serviceId,
            });
            
            if (result.success) {
                this.env.services.notification.add(
                    `Connected as @${result.username}. Rate limit: ${result.rate_limit_remaining}`,
                    { type: "success" }
                );
            } else {
                this.env.services.notification.add(
                    "Connection failed: " + result.error,
                    { type: "danger" }
                );
            }
            
        } catch (error) {
            console.error("Connection test error:", error);
            this.env.services.notification.add(
                "Connection test failed: " + error.message,
                { type: "danger" }
            );
        }
    }

    async postTweet(serviceId, text, replyToTweetId = null) {
        try {
            const result = await this.env.services.rpc("/twitter/api/post_tweet", {
                service_id: serviceId,
                text: text,
                reply_to_tweet_id: replyToTweetId,
            });
            
            if (result.success) {
                this.env.services.notification.add(
                    `Tweet posted successfully! ID: ${result.data.tweet_id}`,
                    { type: "success" }
                );
                return result;
            } else {
                this.env.services.notification.add(
                    "Failed to post tweet: " + result.message,
                    { type: "danger" }
                );
                return result;
            }
            
        } catch (error) {
            console.error("Post tweet error:", error);
            this.env.services.notification.add(
                "Failed to post tweet: " + error.message,
                { type: "danger" }
            );
            return { success: false, error: error.message };
        }
    }

    async getTimeline(serviceId, maxResults = 10, excludeReplies = true, excludeRetweets = true) {
        try {
            const result = await this.env.services.rpc("/twitter/api/get_timeline", {
                service_id: serviceId,
                max_results: maxResults,
                exclude_replies: excludeReplies,
                exclude_retweets: excludeRetweets,
            });
            
            if (result.success) {
                this.env.services.notification.add(
                    `Retrieved ${result.data.tweets.length} tweets`,
                    { type: "success" }
                );
                return result;
            } else {
                this.env.services.notification.add(
                    "Failed to get timeline: " + result.message,
                    { type: "danger" }
                );
                return result;
            }
            
        } catch (error) {
            console.error("Get timeline error:", error);
            this.env.services.notification.add(
                "Failed to get timeline: " + error.message,
                { type: "danger" }
            );
            return { success: false, error: error.message };
        }
    }
}

// Register the component as a service
registry.category("services").add("twitterOAuth", {
    dependencies: ["rpc", "notification"],
    start(env, { rpc, notification }) {
        return new TwitterOAuthComponent(env);
    },
});

export { TwitterOAuthComponent };