import time
import requests
from twitchAPI.helper import first
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticationStorageHelper
from twitchAPI.object.eventsub import (
    ChannelAdBreakBeginEvent,
    ChannelChatMessageDeleteEvent,
    ChannelChatMessageEvent,
    ChannelChatNotificationEvent,
    ChannelChatSettingsUpdateEvent,
    ChannelChatUserMessageHoldEvent,
    ChannelChatUserMessageUpdateEvent,
    ChannelCheerEvent,
    ChannelFollowEvent,
    ChannelModerateEvent,
    ChannelPointsAutomaticRewardRedemptionAddEvent,
    ChannelPointsCustomRewardAddEvent,
    ChannelPointsCustomRewardRedemptionAddEvent,
    ChannelPointsCustomRewardRedemptionUpdateEvent,
    ChannelPointsCustomRewardRemoveEvent,
    ChannelPointsCustomRewardUpdateEvent,
    ChannelPredictionEndEvent,
    ChannelPredictionEvent,
    ChannelPollBeginEvent,
    ChannelPollEndEvent,
    ChannelPollProgressEvent,
    ChannelRaidEvent,
    ChannelShoutoutCreateEvent,
    ChannelSubscribeEvent,
    ChannelSubscriptionEndEvent,
    ChannelSubscriptionGiftEvent,
    ChannelSubscriptionMessageEvent,
    ChannelUpdateEvent,
    ChannelWarningSendEvent,
    CharityCampaignStartEvent,
    CharityCampaignStopEvent,
    CharityDonationEvent,
    GoalEvent,
    HypeTrainEndEvent,
    HypeTrainEvent,
    ShieldModeEvent,
    StreamOfflineEvent,
    StreamOnlineEvent,
    UserWhisperMessageEvent,
    ChannelShoutoutReceiveEvent,
    CharityCampaignProgressEvent,
    ChannelWarningAcknowledgeEvent,
    ChannelSuspiciousUserUpdateEvent,
    ChannelSuspiciousUserMessageEvent,
)
from twitchAPI.eventsub.websocket import EventSubWebsocket
from twitchAPI.type import AuthScope
import asyncio
from thefuzz import fuzz
from utils import get_characters_from_db


Currency_0 = [
    "BIF",
    "CLP",
    "DJF",
    "GNF",
    "ISK",
    "JPY",
    "KMF",
    "KRW",
    "PYG",
    "RWF",
    "UGX",
    "UYI",
    "VND",
    "VUV",
    "XAF",
    "XOF",
    "XPF"
]

Currency_3 = [
    "BHD",
    "IQD",
    "JOD",
    "KWD",
    "LYD",
    "OMR",
    "TND"
]

Currency_4 = [
    "CLF",
    "UYW",
]

characters = get_characters_from_db()

def twitch_events(**kwargs):

    def forward_event_text_to_api(event):
        print(event)
        requests.post("http://127.0.0.1:5275/twitchEvent", json=event, headers={"Content-Type": "application/json"})

    def forward_event_to_speak(event):
        print(event)
        requests.post("http://127.0.0.1:5275/speak", json=event)

    APP_ID = kwargs["app_id"]
    APP_SECRET = kwargs["app_secret"]
    TARGET_SCOPES = [
        AuthScope.ANALYTICS_READ_EXTENSION,
        AuthScope.ANALYTICS_READ_GAMES,
        AuthScope.BITS_READ,
        AuthScope.CHANNEL_BOT,
        AuthScope.CHANNEL_EDIT_COMMERCIAL,
        AuthScope.CHANNEL_MANAGE_ADS,
        AuthScope.CHANNEL_MANAGE_BROADCAST,
        AuthScope.CHANNEL_MANAGE_MODERATORS,
        AuthScope.CHANNEL_MANAGE_POLLS,
        AuthScope.CHANNEL_MANAGE_PREDICTIONS,
        AuthScope.CHANNEL_MANAGE_RAIDS,
        AuthScope.CHANNEL_MANAGE_REDEMPTIONS,
        AuthScope.CHANNEL_MANAGE_SCHEDULE,
        AuthScope.CHANNEL_MANAGE_VIDEOS,
        AuthScope.CHANNEL_MODERATE,
        AuthScope.CHANNEL_READ_ADS,
        AuthScope.CHANNEL_READ_CHARITY,
        AuthScope.CHANNEL_READ_EDITORS,
        AuthScope.CHANNEL_READ_GOALS,
        AuthScope.CHANNEL_READ_HYPE_TRAIN,
        AuthScope.CHANNEL_READ_POLLS,
        AuthScope.CHANNEL_READ_PREDICTIONS,
        AuthScope.CHANNEL_READ_REDEMPTIONS,
        AuthScope.CHANNEL_READ_STREAM_KEY,
        AuthScope.CHANNEL_READ_SUBSCRIPTIONS,
        AuthScope.CHANNEL_READ_VIPS,
        AuthScope.CHANNEL_MANAGE_VIPS,
        AuthScope.CHAT_EDIT,
        AuthScope.CHAT_READ,
        AuthScope.CLIPS_EDIT,
        AuthScope.MODERATION_READ,
        AuthScope.MODERATOR_MANAGE_ANNOUNCEMENTS,
        AuthScope.MODERATOR_MANAGE_AUTOMOD,
        AuthScope.MODERATOR_MANAGE_AUTOMOD_SETTINGS,
        AuthScope.MODERATOR_MANAGE_BANNED_USERS,
        AuthScope.MODERATOR_MANAGE_BLOCKED_TERMS,
        AuthScope.MODERATOR_MANAGE_CHAT_MESSAGES,
        AuthScope.MODERATOR_MANAGE_CHAT_SETTINGS,
        AuthScope.MODERATOR_MANAGE_SHIELD_MODE,
        AuthScope.MODERATOR_MANAGE_UNBAN_REQUESTS,
        AuthScope.MODERATOR_MANAGE_WARNINGS,
        AuthScope.MODERATOR_READ_AUTOMOD_SETTINGS,
        AuthScope.MODERATOR_READ_BANNED_USERS,
        AuthScope.MODERATOR_READ_BLOCKED_TERMS,
        AuthScope.MODERATOR_READ_CHAT_MESSAGES,
        AuthScope.MODERATOR_READ_CHAT_SETTINGS,
        AuthScope.MODERATOR_READ_CHATTERS,
        AuthScope.MODERATOR_READ_FOLLOWERS,
        AuthScope.MODERATOR_READ_MODERATORS,
        AuthScope.MODERATOR_READ_SHIELD_MODE,
        AuthScope.MODERATOR_READ_SHOUTOUTS,
        AuthScope.MODERATOR_READ_SUSPICIOUS_USERS,
        AuthScope.MODERATOR_READ_UNBAN_REQUESTS,
        AuthScope.MODERATOR_READ_WARNINGS,
        AuthScope.MODERATOR_READ_VIPS,
        AuthScope.USER_BOT,
        AuthScope.USER_EDIT,
        AuthScope.USER_EDIT_BROADCAST,
        AuthScope.USER_EDIT_FOLLOWS,
        AuthScope.USER_MANAGE_BLOCKED_USERS,
        AuthScope.USER_MANAGE_CHAT_COLOR,
        AuthScope.USER_MANAGE_WHISPERS,
        AuthScope.USER_READ_BROADCAST,
        AuthScope.USER_READ_CHAT,
        AuthScope.USER_READ_EMAIL,
        AuthScope.USER_READ_EMOTES,
        AuthScope.USER_READ_FOLLOWS,
        AuthScope.USER_READ_MODERATED_CHANNELS,
        AuthScope.USER_READ_SUBSCRIPTIONS,
        AuthScope.USER_READ_WHISPERS,
        AuthScope.USER_WRITE_CHAT,
        AuthScope.WHISPERS_EDIT,
        AuthScope.WHISPERS_READ,
    ]

    async def on_channel_ad_break_begin(data: ChannelAdBreakBeginEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'{"Automatic" if data.event.is_automatic else "Manual"} ad break begin event: Duration {data.event.duration_seconds}'})

    async def on_channel_chat_message(data: ChannelChatMessageEvent):
        c = False
        chatter = data.event.chatter_user_name.lower()
        if ":" in data.event.message.text:
            command = data.event.message.text.split(":")[0].lower()
            print(f"checking message: {data.event.message.text}")
            for character in characters:
                username = characters[character].username.lower()
                print(f"checking character: |{command}| |{username}|")
                if username == command:
                    print(f"found character: {username}")
                    c = True
                    forward_event_to_speak({"character": characters[character].username.lower(), "message": data.event.message.text[len(characters[character].username)+1:], "source": "user chat"})
                    break
        else:
            if chatter in characters:
                forward_event_to_speak({"character": chatter, "message": data.event.message.text, "source": "real chat"})
                c = True
        if not c:
            print(f"not found: {data.event.chatter_user_name}")
            forward_event_text_to_api({"source": data.event.chatter_user_name, "message": f'Chat message from {data.event.chatter_user_name}: {data.event.message.text}'})

    async def on_channel_chat_message_delete(data: ChannelChatMessageDeleteEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Chat message from {data.event.target_user_name} was deleted'})

    async def on_channel_chat_notification(data: ChannelChatNotificationEvent):
        forward_event_text_to_api({"source": data.event.chatter_user_name, "message": f'Channel chat notification event: {data.event.notice_type}'})

    async def on_channel_chat_settings_update(data: ChannelChatSettingsUpdateEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Channel chat settings updated event'})

    async def on_channel_chat_user_message_hold(data: ChannelChatUserMessageHoldEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Channel chat user message hold event: {data.event.message_id}'})

    async def on_channel_chat_user_message_update(data: ChannelChatUserMessageUpdateEvent):
        forward_event_text_to_api({"source": data.event.user_name, "message": f'Channel chat user message update event: {data.event.message}'})

    async def on_channel_cheer(data: ChannelCheerEvent):
        forward_event_text_to_api({"source": "Anonymous" if data.event.is_anonymous else data.event.user_name, "message": f'{"Anonymous" if data.event.is_anonymous else data.event.user_name} cheered {data.event.bits} bits: {data.event.message}'})

    async def on_channel_follow(data: ChannelFollowEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Channel follow event: {data.event.user_name} now follows {data.event.broadcaster_user_name}'})

    async def on_channel_moderate(data: ChannelModerateEvent):
        if (data.event.action == "ban"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Viewer {data.event.ban.user_name} was banned for {data.event.ban.reason} by {data.event.moderator_user_name}'})
        elif (data.event.action == "timeout"):
            time_difference = data.event.timeout.expires_at - time.time()
            days = time_difference.days
            hours, remainder = divmod(time_difference.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_string = ""
            if days > 0:
                time_string += f'{days} days '
            if hours > 0:
                time_string += f'{hours} hours '
            if minutes > 0:
                time_string += f'{minutes} minutes '
            if seconds > 0:
                time_string += f'{seconds} seconds '
            forward_event_text_to_api({"source": "Twitch", "message": f'Viewer {data.event.timeout.user_name} was timed out for {time_string} by {data.event.moderator_user_name}'})
        elif (data.event.action == "unban"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Viewer {data.event.unban.user_name} was unbanned by {data.event.moderator_user_name}'})
        elif (data.event.action == "untimeout"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Viewer {data.event.untimeout} was untimed out by {data.event.moderator_user_name}'})
        elif (data.event.action == "clear"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Chat was cleared by {data.event.moderator_user_name}'})
        elif (data.event.action == "emoteonly"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Emote only mode enabled by {data.event.moderator_user_name}'})
        elif (data.event.action == "emoteonlyoff"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Emote only mode disabled by {data.event.moderator_user_name}'})
        elif (data.event.action == "followers"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Followers only mode enabled by {data.event.moderator_user_name}'})
        elif (data.event.action == "followersoff"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Followers only mode disabled by {data.event.moderator_user_name}'})
        elif (data.event.action == "uniquechat"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Unique chat enabled by {data.event.moderator_user_name}'})
        elif (data.event.action == "uniquechatoff"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Unique chat disabled by {data.event.moderator_user_name}'})
        elif (data.event.action == "slow"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Slow mode enabled: {data.event.slow.wait_time_seconds} seconds by {data.event.moderator_user_name}'})
        elif (data.event.action == "slowoff"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Slow mode disabled by {data.event.moderator_user_name}'})
        elif (data.event.action == "subscribers"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Subscribers only mode enabled by {data.event.moderator_user_name}'})
        elif (data.event.action == "subscribersoff"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Subscribers only mode disabled by {data.event.moderator_user_name}'})
        elif (data.event.action == "unraid"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Raid Cancelled by {data.event.moderator_user_name}'})
        elif (data.event.action == "delete"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Message from {data.event.delete.user_name} was deleted by {data.event.moderator_user_name}'})
        elif (data.event.action == "vip"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Viewer {data.event.vip.user_name} was added as VIP by {data.event.moderator_user_name}'})
        elif (data.event.action == "unvip"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Viewer {data.event.unvip.user_name} was removed as VIP by {data.event.moderator_user_name}'})
        elif (data.event.action == "raid"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Starting Raid on {data.event.raid.user_name} with {data.event.raid.viewer_count} viewers started by {data.event.moderator_user_name}'})
        elif (data.event.action == "add_blocked_term"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Blocked term(s) added: {data.event.automod_terms.terms} by {data.event.moderator_user_name}'})
        elif (data.event.action == "add_permitted_term"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Permitted term(s) added: {data.event.automod_terms.terms} by {data.event.moderator_user_name}'})
        elif (data.event.action == "remove_blocked_term"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Blocked term(s) removed: {data.event.automod_terms.terms} by {data.event.moderator_user_name}'})
        elif (data.event.action == "remove_permitted_term"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Permitted term(s) removed: {data.event.automod_terms.terms} by {data.event.moderator_user_name}'})
        elif (data.event.action == "mod"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Viewer {data.event.mod.user_name} added as moderator by {data.event.moderator_user_name}'})
        elif (data.event.action == "unmod"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Viewer {data.event.unmod.user_name} removed as moderator by {data.event.moderator_user_name}'})
        elif (data.event.action == "approve_unban_request"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Unban request approved for {data.event.unban_request.user_name} by {data.event.moderator_user_name}'})
        elif (data.event.action == "deny_unban_request"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Unban request denied for {data.event.unban_request.user_name} by {data.event.moderator_user_name}'})
        elif (data.event.action == "warn"):
            forward_event_text_to_api({"source": "Twitch", "message": f'Warning sent to {data.event.warn.user_name} by {data.event.moderator_user_name} for {data.event.warn.chat_rules_cited} | Reason: {data.event.warn.reason}'})


    async def on_channel_points_automatic_reward_redemption_add(data: ChannelPointsAutomaticRewardRedemptionAddEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Viewer {data.event.user_name} redeemed: {data.event.reward.to_dict()}'})

    async def on_channel_points_custom_reward_add(data: ChannelPointsCustomRewardAddEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'New Channel Point Redeem added: {data.event.title} for {data.event.cost} Points'})

    async def on_channel_points_custom_reward_redemption_add(data: ChannelPointsCustomRewardRedemptionAddEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Viewer {data.event.user_name} redeemed: {data.event.reward.to_dict()}'})

    async def on_channel_points_custom_reward_redemption_update(data: ChannelPointsCustomRewardRedemptionUpdateEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Channel Point Redeem updated: {data.event.user_name} for {data.event.cost} Points'})

    async def on_channel_points_custom_reward_remove(data: ChannelPointsCustomRewardRemoveEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Channel points reward {data.event.title} removed'})

    async def on_channel_points_custom_reward_update(data: ChannelPointsCustomRewardUpdateEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Channel points reward {data.event.title} updated'})

    async def on_channel_prediction_end(data: ChannelPredictionEndEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Prediction {data.event.title} ended. Winning Outcome: {data.event.outcomes[data.event.winning_outcome_id].to_dict()}'})

    async def on_channel_prediction(data: ChannelPredictionEvent):
        current_time = time.time()
        time_difference = (data.event.locks_at - current_time).total_seconds()
        if time_difference > 0:
            forward_event_text_to_api({"source": "Twitch", "message": f'Ongoing prediction: {data.event.title}, locks in {time_difference} seconds'})
        else:
            total_points = sum([outcome.channel_points for outcome in data.event.outcomes])
            forward_event_text_to_api({"source": "Twitch", "message": f'Ongoing prediction: {data.event.title} is locked with {total_points} channel points'})

    async def on_channel_poll_begin(data: ChannelPollBeginEvent):
        current_time = time.time()
        time_difference = (data.event.locks_at - current_time).total_seconds()
        forward_event_text_to_api({"source": "Twitch", "message": f'Starting Poll: {data.event.title} ends in {time_difference} seconds'})

    async def on_channel_poll_end(data: ChannelPollEndEvent):
        winning_option = max(data.event.choices, key=lambda x: x.votes)
        total_votes = sum([option.votes for option in data.event.choices])
        forward_event_text_to_api({"source": "Twitch", "message": f'Poll {data.event.title} ended. Winning Option: {winning_option.title} with {winning_option.votes / total_votes * 100}% of the votes'})

    async def on_channel_poll_progress(data: ChannelPollProgressEvent):
        winning_option = max(data.event.choices, key=lambda x: x.votes)
        total_votes = sum([option.votes for option in data.event.choices])
        forward_event_text_to_api({"source": "Twitch", "message": f'Poll {data.event.title} in progress. Winning Option: {winning_option.title} with {winning_option.votes / total_votes * 100}% of the votes'})

    async def on_channel_raid(data: ChannelRaidEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'{data.event.from_broadcaster_user_name} is raiding us with {data.event.viewers} viewers!'})

    async def on_channel_shoutout_create(data: ChannelShoutoutCreateEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Shoutout created for {data.event.to_broadcaster_user_name}'})

    async def on_channel_subscribe(data: ChannelSubscribeEvent):
        if data.event.is_gift:
            forward_event_text_to_api({"source": "Twitch", "message": f'Viewer {data.event.user_name} was gifted a tier {int(data.event.tier) / 1000} subscription '})
        else:
            forward_event_text_to_api({"source": "Twitch", "message": f'Viewer {data.event.user_name} subscribed at tier {int(data.event.tier) / 1000}'})

    async def on_channel_subscription_end(data: ChannelSubscriptionEndEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Viewer {data.event.user_name}\'s subscription has ended'})

    async def on_channel_subscription_gift(data: ChannelSubscriptionGiftEvent):
        if data.event.is_anonymous:
            forward_event_text_to_api({"source": "Twitch", "message": f'An anonymous user gifted {data.event.total} subscriptions to the community!'})
        else:
            forward_event_text_to_api({"source": "Twitch", "message": f'Viewer {data.event.user_name} just gifted {data.event.total} subscriptions to the community! They have gifted {data.event.cumulative_total} in total'})

    async def on_channel_subscription_message(data: ChannelSubscriptionMessageEvent):
        if data.event.cumulative_months and data.event.cumulative_months > 1:
            forward_event_text_to_api({"source": "Twitch", "message": f'Viewer {data.event.user_name} subscribed for {data.event.duration_months} months at tier {int(data.event.tier) / 1000}. They have been active for {data.event.cumulative_months} months.'})
        else:
            forward_event_text_to_api({"source": "Twitch", "message": f'Viewer {data.event.user_name} subscribed for {data.event.duration_months} months at tier {int(data.event.tier) / 1000}!'})

    async def on_channel_update(data: ChannelUpdateEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Stream Description Updated: {data.event.title} | in category: {data.event.category_name} | Labels: {data.event.content_classification_labels}'})

    async def on_channel_warning_send(data: ChannelWarningSendEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Warning sent to {data.event.user_name} for {data.event.chat_rules_cited} | Reason: {data.event.reason}'})

    async def on_charity_campaign_start(data: CharityCampaignStartEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Charity campaign started for: {data.event.charity_name} | Goal: {data.event.target_amount}'})

    async def on_charity_campaign_stop(data: CharityCampaignStopEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Charity campaign stopped for: {data.event.charity_name} | Raised: {data.event.current_amount}'})

    async def on_charity_donation(data: CharityDonationEvent):
        adjusted_amount = data.event.amount.value
        if data.event.amount.currency in Currency_0:
            adjusted_amount = data.event.amount.value
        elif data.event.amount.currency in Currency_3:
            adjusted_amount = data.event.amount.value / 1000
        elif data.event.amount.currency in Currency_4:
            adjusted_amount = data.event.amount.value / 10000
        else:
            adjusted_amount = data.event.amount.value / 100
        if {data.event.amount.currency} == 'USD':
            forward_event_text_to_api({"source": "Twitch", "message": f'Viewer {data.event.user_name} donated {adjusted_amount:.2f} {data.event.amount.currency} to {data.event.charity_name}'})


    async def on_charity_campaign_progress(data: CharityCampaignProgressEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Charity campaign for {data.event.charity_name} has raised {data.event.current_amount} of {data.event.target_amount}'})

    # async def on_drop_entitlement_grant(data: DropEntitlementGrantEvent):
    #     forward_event_text_to_api({"source": "Twitch", "message": f'Entitlement granted: {data.event.entitlement_id}'})

    async def on_goal(data: GoalEvent):
        if data.event.type == 'follow':
            forward_event_text_to_api({"source": "Twitch", "message": f'Goal: Followers: {data.event.current_amount}/{data.event.target_amount}'})
        elif data.event.type == 'subscription':
            forward_event_text_to_api({"source": "Twitch", "message": f'Goal: Subscriptions: {data.event.current_amount}/{data.event.target_amount}'})
        elif data.event.type == 'subscription_count':
            forward_event_text_to_api({"source": "Twitch", "message": f'Goal: Unique Subscribers: {data.event.current_amount}/{data.event.target_amount}'})
        elif data.event.type == 'new_subscription':
            forward_event_text_to_api({"source": "Twitch", "message": f'Goal: New Subscriptions: {data.event.current_amount}/{data.event.target_amount}'})
        elif data.event.type == 'new_subscription_count':
            forward_event_text_to_api({"source": "Twitch", "message": f'Goal: Unique New Subscribers: {data.event.current_amount}/{data.event.target_amount}'})

    async def on_hype_train_end(data: HypeTrainEndEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Hype Train ended at level {data.event.level}'})

    async def on_hype_train(data: HypeTrainEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Hype Train at level {data.event.level} | {data.event.progress / data.event.goal * 100}%'})

    async def on_shield_mode(data: ShieldModeEvent):
        if hasattr(data.event, 'started_at'):
            forward_event_text_to_api({"source": "Twitch", "message": f'Shield Mode enabled at {data.event.started_at}'})
        else:
            forward_event_text_to_api({"source": "Twitch", "message": f'Shield Mode disabled at {data.event.ended_at}'})

    async def on_stream_offline(data: StreamOfflineEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Stream went offline'})

    async def on_stream_online(data: StreamOnlineEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Stream went online at {data.event.started_at}'})

    # async def on_user_authorization_grant(data: UserAuthorizationGrantEvent):
    #     forward_event_text_to_api({"source": "Twitch", "message": f'User {data.event.user_name} granted authorization'})

    # async def on_user_authorization_revoke(data: UserAuthorizationRevokeEvent):
    #     forward_event_text_to_api({"source": "Twitch", "message": f'User {data.event.user_name} revoked authorization'})

    # async def on_user_update(data: UserUpdateEvent):
    #     forward_event_text_to_api({"source": "Twitch", "message": f'User {data.event.user_name} updated'})

    async def on_user_whisper_message(data: UserWhisperMessageEvent):
        pass
        # forward_event_text_to_api({"source": "Twitch", "message": f'Whisper from {data.event.from_user_name}: {data.event.whisper.text}'})

    async def on_channel_shoutout_receive(data: ChannelShoutoutReceiveEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Shoutout received from {data.event.from_broadcaster_user_name}'})

    async def on_channel_warning_acknowledge(data: ChannelWarningAcknowledgeEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Warning acknowledged by {data.event.user_name}'})

    async def on_channel_suspicious_user_update(data: ChannelSuspiciousUserUpdateEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Viewer {data.event.user_name} has been marked as {"suspicious" if data.event.low_trust_status == "none" else "not suspicious"}'})

    async def on_channel_suspicious_user_message(data: ChannelSuspiciousUserMessageEvent):
        forward_event_text_to_api({"source": "Twitch", "message": f'Chat message from suspicious viewer {data.event.user_name}: {data.event.message.text}'})

    async def run():
        # create the api instance and get user auth either from storage or website
        twitch = await Twitch(APP_ID, APP_SECRET)
        helper = UserAuthenticationStorageHelper(twitch, TARGET_SCOPES)
        await helper.bind()

        # get the currently logged in user
        user = await first(twitch.get_users())

        # create eventsub websocket instance and start the client.
        eventsub = EventSubWebsocket(twitch)
        eventsub.start()
        # subscribing to the desired eventsub hook for our user
        # the given function (in this example on_follow) will be called every time this event is triggered
        # the broadcaster is a moderator in their own channel by default so specifying both as the same works in this example
        # We have to subscribe to the first topic within 10 seconds of eventsub.start() to not be disconnected.

        await eventsub.listen_channel_ad_break_begin(user.id, on_channel_ad_break_begin)
        await eventsub.listen_channel_chat_message(user.id, user.id, on_channel_chat_message)
        await eventsub.listen_channel_chat_message_delete(user.id, user.id, on_channel_chat_message_delete)
        await eventsub.listen_channel_chat_notification(user.id, user.id, on_channel_chat_notification)
        await eventsub.listen_channel_chat_settings_update(user.id, user.id, on_channel_chat_settings_update)
        await eventsub.listen_channel_chat_user_message_hold(user.id, user.id, on_channel_chat_user_message_hold)
        await eventsub.listen_channel_chat_user_message_update(user.id, user.id, on_channel_chat_user_message_update)
        await eventsub.listen_channel_cheer(user.id, on_channel_cheer)
        await eventsub.listen_channel_follow_v2(user.id, user.id, on_channel_follow)
        await eventsub.listen_channel_moderate(user.id, user.id, on_channel_moderate)
        await eventsub.listen_channel_points_automatic_reward_redemption_add(user.id, on_channel_points_automatic_reward_redemption_add)
        await eventsub.listen_channel_points_custom_reward_add(user.id, on_channel_points_custom_reward_add)
        await eventsub.listen_channel_points_custom_reward_redemption_add(user.id, on_channel_points_custom_reward_redemption_add)
        await eventsub.listen_channel_points_custom_reward_redemption_update(user.id, on_channel_points_custom_reward_redemption_update)
        await eventsub.listen_channel_points_custom_reward_remove(user.id, on_channel_points_custom_reward_remove)
        await eventsub.listen_channel_points_custom_reward_update(user.id, on_channel_points_custom_reward_update)
        await eventsub.listen_channel_prediction_begin(user.id, on_channel_prediction)
        await eventsub.listen_channel_prediction_progress(user.id, on_channel_prediction)
        await eventsub.listen_channel_prediction_end(user.id, on_channel_prediction_end)
        await eventsub.listen_channel_poll_begin(user.id, on_channel_poll_begin)
        await eventsub.listen_channel_poll_end(user.id, on_channel_poll_end)
        await eventsub.listen_channel_poll_progress(user.id, on_channel_poll_progress)
        await eventsub.listen_channel_raid(on_channel_raid, user.id)
        await eventsub.listen_channel_shoutout_create(user.id, user.id, on_channel_shoutout_create)
        await eventsub.listen_channel_subscribe(user.id, on_channel_subscribe)
        await eventsub.listen_channel_subscription_end(user.id, on_channel_subscription_end)
        await eventsub.listen_channel_subscription_gift(user.id, on_channel_subscription_gift)
        await eventsub.listen_channel_subscription_message(user.id, on_channel_subscription_message)
        await eventsub.listen_channel_update_v2(user.id, on_channel_update)
        await eventsub.listen_channel_warning_send(user.id, user.id, on_channel_warning_send)
        await eventsub.listen_channel_charity_campaign_start(user.id, on_charity_campaign_start)
        await eventsub.listen_channel_charity_campaign_stop(user.id, on_charity_campaign_stop)
        await eventsub.listen_channel_charity_campaign_donate(user.id, on_charity_donation)
        await eventsub.listen_channel_charity_campaign_progress(user.id, on_charity_campaign_progress)
        # await eventsub.listen_drop_entitlement_grant(user.id, user.id, on_drop_entitlement_grant)
        await eventsub.listen_goal_begin(user.id, on_goal)
        await eventsub.listen_hype_train_begin(user.id, on_hype_train)
        await eventsub.listen_hype_train_progress( user.id, on_hype_train)
        await eventsub.listen_hype_train_end(user.id, on_hype_train_end)
        await eventsub.listen_channel_shield_mode_begin(user.id, user.id, on_shield_mode)
        await eventsub.listen_channel_shield_mode_end(user.id, user.id, on_shield_mode)
        await eventsub.listen_stream_offline(user.id, on_stream_offline)
        await eventsub.listen_stream_online(user.id, on_stream_online)
        # await eventsub.listen_user_authorization_grant(APP_ID, on_user_authorization_grant)
        # await eventsub.listen_user_authorization_revoke(APP_ID, on_user_authorization_revoke)
        # await eventsub.listen_user_update(user.id, user.id, on_user_update)
        await eventsub.listen_user_whisper_message(user.id, on_user_whisper_message)
        await eventsub.listen_channel_shoutout_receive(user.id, user.id, on_channel_shoutout_receive)
        await eventsub.listen_channel_warning_acknowledge(user.id, user.id, on_channel_warning_acknowledge)
        await eventsub.listen_channel_suspicious_user_update(user.id, user.id, on_channel_suspicious_user_update)
        await eventsub.listen_channel_suspicious_user_message(user.id, user.id, on_channel_suspicious_user_message)
        # await eventsub.listen_extension_bits_transaction_create(EXTENSION_ID, on_extension_bits_transaction_create)

        # eventsub will run in its own process
        # so lets just wait for user input before shutting it all down again
        try:
            await asyncio.sleep(100000)
        except KeyboardInterrupt:
            pass
        finally:
            # stopping both eventsub as well as gracefully closing the connection to the API
            await eventsub.stop()
            await twitch.close()
    
    asyncio.run(run())
