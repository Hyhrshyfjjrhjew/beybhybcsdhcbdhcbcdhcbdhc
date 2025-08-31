


# Alternative approach: Pre-scan messages to identify media groups
@bot.on_message(filters.command("bdl2") & filters.private)  # Alternative command for testing
async def download_range_advanced(bot: Client, message: Message):
    """
    Advanced batch download that pre-scans for media groups
    """
    args = message.text.split()

    if len(args) != 3 or not all(arg.startswith("https://t.me/") for arg in args[1:]):
        await message.reply(
            "🚀 **Advanced Batch Download Process**\n"
            "`/bdl2 start_link end_link`\n\n"
            "💡 **Example:**\n"
            "`/bdl2 https://t.me/mychannel/100 https://t.me/mychannel/120`"
        )
        return

    try:
        start_chat, start_thread, start_id = getChatMsgID(args[1])
        end_chat, end_thread, end_id = getChatMsgID(args[2])
    except Exception as e:
        return await message.reply(f"**❌ Error parsing links:\n{e}**")

    if start_chat != end_chat:
        return await message.reply("**❌ Both links must be from the same channel.**")
    
    if start_thread != end_thread:
        return await message.reply("**❌ Both links must be from the same topic thread.**")
        
    if start_id > end_id:
        return await message.reply("**❌ Invalid range: start ID cannot exceed end ID.**")

    loading = await message.reply("📥 **Pre-scanning messages for media groups...**")
    
    # Pre-scan phase: identify media groups and their representative messages
    media_groups = {}  # media_group_id -> first_message_id
    valid_messages = []  # List of message IDs to download
    
    for msg_id in range(start_id, end_id + 1):
        try:
            chat_msg = await user.get_messages(chat_id=start_chat, message_ids=msg_id)
            
            if not chat_msg or chat_msg.empty:
                continue
                
            # If this is a forum topic range, verify the message belongs to the topic
            if start_thread and not message_belongs_to_topic(chat_msg, start_thread):
                continue
                
            has_media = bool(chat_msg.media_group_id or chat_msg.media)
            has_text = bool(chat_msg.text or chat_msg.caption)
            if not (has_media or has_text):
                continue
                
            if chat_msg.media_group_id:
                if chat_msg.media_group_id not in media_groups:
                    # This is the first message in this media group
                    media_groups[chat_msg.media_group_id] = msg_id
                    valid_messages.append(msg_id)
                # Skip subsequent messages in the same media group
            else:
                valid_messages.append(msg_id)
                
        except Exception as e:
            LOGGER(__name__).error(f"Error scanning message {msg_id}: {e}")
            continue
    
    await loading.edit_text(f"📥 **Found {len(valid_messages)} unique messages to download (including {len(media_groups)} media groups)...**")
    
    # Download phase
    if start_thread:
        prefix = args[1].rsplit("/", 1)[0]
    else:
        prefix = args[1].rsplit("/", 1)[0]
        
    downloaded = failed = 0
    
    for i, msg_id in enumerate(valid_messages, 1):
        url = f"{prefix}/{msg_id}"
        try:
            await loading.edit_text(f"📥 **Downloading {i}/{len(valid_messages)}...**")
            
            task = track_task(handle_download(bot, message, url))
            await task
            downloaded += 1
            
        except asyncio.CancelledError:
            await loading.delete()
            return await message.reply(f"**❌ Batch canceled** after downloading `{downloaded}` posts.")
        except Exception as e:
            failed += 1
            LOGGER(__name__).error(f"Error downloading {url}: {e}")
            
        await asyncio.sleep(3)
    
    await loading.delete()
    
    # Final results
    total_range = end_id - start_id + 1
    skipped = total_range - len(valid_messages)
    
    result_message = (
        "**✅ Advanced Batch Process Complete!**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"📥 **Downloaded** : `{downloaded}` unique post(s)\n"
        f"📦 **Media groups**: `{len(media_groups)}` (preventing duplicates)\n"
        f"⏭️ **Skipped**    : `{skipped}` (no content/deleted/duplicates)\n"
        f"❌ **Failed**     : `{failed}` error(s)\n"
        f"📊 **Total range**: `{total_range}` messages"
    )
    
    if start_thread:
        result_message += f"\n📁 **Forum Topic**: {start_thread}"
    
    await message.reply(result_message)