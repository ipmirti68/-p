#!/bin/sh
mkdir -p /usr/share/nginx/html/cam{1..7}
nginx &

# En uzun videoyu hepsinde kullan ki donmasın - ocean.mp4
VID="/app/ocean.mp4"

ffmpeg -re -stream_loop -1 -i $VID -re -reconnect 1 -reconnect_streamed 1 -i https://sslyayin.netyayin.net/aksarayinsesi/stream/ -map 0:v -map 1:a -c:v libx264 -preset ultrafast -b:v 800k -r 20 -vf scale=960:540 -c:a aac -b:a 64k -f hls -hls_time 4 -hls_list_size 6 -hls_flags delete_segments+omit_endlist /usr/share/nginx/html/cam1/playlist.m3u8 &

ffmpeg -re -stream_loop -1 -i $VID -re -reconnect 1 -reconnect_streamed 1 -i https://radyo.yayindakiler.com:4026/stream -map 0:v -map 1:a -c:v libx264 -preset ultrafast -b:v 800k -r 20 -vf scale=960:540 -c:a aac -b:a 64k -f hls -hls_time 4 -hls_list_size 6 -hls_flags delete_segments+omit_endlist /usr/share/nginx/html/cam2/playlist.m3u8 &

ffmpeg -re -stream_loop -1 -i $VID -re -reconnect 1 -reconnect_streamed 1 -i https://stream.turkiyeradyolari.com/aksarayfm/stream?/; -map 0:v -map 1:a -c:v libx264 -preset ultrafast -b:v 800k -r 20 -vf scale=960:540 -c:a aac -b:a 64k -f hls -hls_time 4 -hls_list_size 6 -hls_flags delete_segments+omit_endlist /usr/share/nginx/html/cam3/playlist.m3u8 &

ffmpeg -re -stream_loop -1 -i $VID -re -reconnect 1 -reconnect_streamed 1 -i https://radyo.yayindakiler.com:4022/stream -map 0:v -map 1:a -c:v libx264 -preset ultrafast -b:v 800k -r 20 -vf scale=960:540 -c:a aac -b:a 64k -f hls -hls_time 4 -hls_list_size 6 -hls_flags delete_segments+omit_endlist /usr/share/nginx/html/cam4/playlist.m3u8 &

ffmpeg -re -stream_loop -1 -i $VID -re -reconnect 1 -reconnect_streamed 1 -i https://radyo.yayindakiler.com:4036/stream -map 0:v -map 1:a -c:v libx264 -preset ultrafast -b:v 800k -r 20 -vf scale=960:540 -c:a aac -b:a 64k -f hls -hls_time 4 -hls_list_size 6 -hls_flags delete_segments+omit_endlist /usr/share/nginx/html/cam5/playlist.m3u8 &

ffmpeg -re -stream_loop -1 -i $VID -re -reconnect 1 -reconnect_streamed 1 -i https://moondigitaledge.radyotvonline.net/turkulerleturkiye/playlist.m3u8 -map 0:v -map 1:a -c:v libx264 -preset ultrafast -b:v 800k -r 20 -vf scale=960:540 -c:a aac -b:a 64k -f hls -hls_time 4 -hls_list_size 6 -hls_flags delete_segments+omit_endlist /usr/share/nginx/html/cam6/playlist.m3u8 &

ffmpeg -re -stream_loop -1 -i $VID -re -reconnect 1 -reconnect_streamed 1 -i https://yayin.turkhosted.com/4591/stream -map 0:v -map 1:a -c:v libx264 -preset ultrafast -b:v 800k -r 20 -vf scale=960:540 -c:a aac -b:a 64k -f hls -hls_time 4 -hls_list_size 6 -hls_flags delete_segments+omit_endlist /usr/share/nginx/html/cam7/playlist.m3u8 &

wait
