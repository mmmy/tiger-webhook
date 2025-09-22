#!/usr/bin/env python3
"""
测试SOCKS5代理是否可用
"""

import socket
import requests
import time
from urllib.parse import urlparse


def test_socks5_connection(proxy_url):
    """测试SOCKS5代理连接"""
    print("=" * 60)
    print("测试SOCKS5代理连接")
    print("=" * 60)
    
    # 解析代理URL
    parsed = urlparse(proxy_url)
    host = parsed.hostname
    port = parsed.port
    
    print(f"代理地址: {host}:{port}")
    
    # 1. 测试TCP连接
    print(f"\n🔍 步骤1: 测试TCP连接到 {host}:{port}")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 5秒超时
        
        start_time = time.time()
        result = sock.connect_ex((host, port))
        end_time = time.time()
        
        if result == 0:
            print(f"✅ TCP连接成功 (耗时: {(end_time - start_time)*1000:.1f}ms)")
            sock.close()
        else:
            print(f"❌ TCP连接失败 (错误代码: {result})")
            return False
            
    except Exception as e:
        print(f"❌ TCP连接异常: {e}")
        return False
    
    # 2. 测试SOCKS5握手
    print(f"\n🔍 步骤2: 测试SOCKS5握手")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        
        # SOCKS5握手 - 发送认证方法
        # 格式: [版本][方法数量][方法列表]
        # 0x05 = SOCKS5, 0x01 = 1个方法, 0x00 = 无认证
        sock.send(b'\x05\x01\x00')
        
        # 接收服务器响应
        response = sock.recv(2)
        if len(response) == 2 and response[0] == 0x05:
            if response[1] == 0x00:
                print(f"✅ SOCKS5握手成功 (无认证)")
            elif response[1] == 0x02:
                print(f"⚠️ SOCKS5需要用户名/密码认证")
            elif response[1] == 0xFF:
                print(f"❌ SOCKS5拒绝所有认证方法")
                sock.close()
                return False
            else:
                print(f"⚠️ SOCKS5返回未知认证方法: {response[1]}")
        else:
            print(f"❌ SOCKS5握手失败 (响应: {response.hex()})")
            sock.close()
            return False
            
        sock.close()
        
    except Exception as e:
        print(f"❌ SOCKS5握手异常: {e}")
        return False
    
    # 3. 测试HTTP请求通过代理
    print(f"\n🔍 步骤3: 测试HTTP请求通过代理")
    try:
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        # 测试访问一个简单的网站
        test_urls = [
            'http://httpbin.org/ip',
            'https://httpbin.org/ip',
            'http://www.google.com',
        ]
        
        for test_url in test_urls:
            try:
                print(f"  测试: {test_url}")
                start_time = time.time()
                
                response = requests.get(
                    test_url, 
                    proxies=proxies, 
                    timeout=10,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                )
                
                end_time = time.time()
                
                if response.status_code == 200:
                    print(f"    ✅ 请求成功 (状态码: {response.status_code}, 耗时: {(end_time - start_time)*1000:.1f}ms)")
                    
                    # 如果是IP检测服务，显示返回的IP
                    if 'httpbin.org/ip' in test_url:
                        try:
                            ip_info = response.json()
                            print(f"    📍 检测到的IP: {ip_info.get('origin', 'N/A')}")
                        except:
                            pass
                else:
                    print(f"    ⚠️ 请求返回状态码: {response.status_code}")
                    
            except requests.exceptions.ProxyError as e:
                print(f"    ❌ 代理错误: {e}")
                return False
            except requests.exceptions.Timeout as e:
                print(f"    ⚠️ 请求超时: {e}")
            except requests.exceptions.ConnectionError as e:
                print(f"    ❌ 连接错误: {e}")
                return False
            except Exception as e:
                print(f"    ❌ 请求异常: {e}")
        
    except Exception as e:
        print(f"❌ HTTP测试异常: {e}")
        return False
    
    # 4. 测试代理性能
    print(f"\n🔍 步骤4: 测试代理性能")
    try:
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        # 测试多次请求的平均延迟
        test_url = 'http://httpbin.org/get'
        times = []
        
        for i in range(3):
            try:
                start_time = time.time()
                response = requests.get(test_url, proxies=proxies, timeout=10)
                end_time = time.time()
                
                if response.status_code == 200:
                    latency = (end_time - start_time) * 1000
                    times.append(latency)
                    print(f"  请求 {i+1}: {latency:.1f}ms")
                    
            except Exception as e:
                print(f"  请求 {i+1}: 失败 ({e})")
        
        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            print(f"  📊 性能统计:")
            print(f"    平均延迟: {avg_time:.1f}ms")
            print(f"    最小延迟: {min_time:.1f}ms")
            print(f"    最大延迟: {max_time:.1f}ms")
            
            if avg_time < 1000:
                print(f"    ✅ 代理性能良好")
            elif avg_time < 3000:
                print(f"    ⚠️ 代理性能一般")
            else:
                print(f"    ❌ 代理性能较差")
        
    except Exception as e:
        print(f"❌ 性能测试异常: {e}")
    
    return True


def test_without_proxy():
    """测试不使用代理的连接作为对比"""
    print(f"\n🔍 对比测试: 不使用代理的连接")
    try:
        start_time = time.time()
        response = requests.get('http://httpbin.org/ip', timeout=10)
        end_time = time.time()
        
        if response.status_code == 200:
            latency = (end_time - start_time) * 1000
            print(f"  ✅ 直连成功 (耗时: {latency:.1f}ms)")
            
            try:
                ip_info = response.json()
                print(f"  📍 本地IP: {ip_info.get('origin', 'N/A')}")
            except:
                pass
        else:
            print(f"  ⚠️ 直连返回状态码: {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ 直连失败: {e}")


def main():
    """主函数"""
    proxy_url = "socks5://127.0.0.1:1080"
    
    print("SOCKS5代理测试工具")
    print(f"测试代理: {proxy_url}")
    
    # 测试代理
    proxy_works = test_socks5_connection(proxy_url)
    
    # 测试直连作为对比
    test_without_proxy()
    
    # 总结
    print(f"\n" + "=" * 60)
    print("🎯 测试总结")
    print("=" * 60)
    
    if proxy_works:
        print("✅ SOCKS5代理可用")
        print("📋 建议:")
        print("  - 可以在应用中使用此代理")
        print("  - 注意监控代理的稳定性和性能")
        print("  - 如果是翻墙代理，请遵守当地法律法规")
    else:
        print("❌ SOCKS5代理不可用")
        print("📋 可能的原因:")
        print("  - 代理服务未启动")
        print("  - 端口1080被占用或被阻止")
        print("  - 防火墙阻止了连接")
        print("  - 代理软件配置错误")
        print("📋 解决建议:")
        print("  - 检查代理软件是否正在运行")
        print("  - 确认端口1080是否正确")
        print("  - 检查防火墙设置")
        print("  - 尝试重启代理软件")


if __name__ == "__main__":
    main()
