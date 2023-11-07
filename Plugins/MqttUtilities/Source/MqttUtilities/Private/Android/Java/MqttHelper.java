// Copyright (c) 2023 T4lus Development

package com.ninevastudios.mqttdemo;

import android.app.Activity;
import android.util.Log;

import org.eclipse.paho.android.service.MqttAndroidClient;
import org.eclipse.paho.client.mqttv3.DisconnectedBufferOptions;
import org.eclipse.paho.client.mqttv3.IMqttActionListener;
import org.eclipse.paho.client.mqttv3.IMqttMessageListener;
import org.eclipse.paho.client.mqttv3.IMqttToken;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.eclipse.paho.client.mqttv3.MqttException;
import org.eclipse.paho.client.mqttv3.MqttMessage;

public class MqttHelper {
	private final String TAG = "MQTT => ";

	private MqttAndroidClient mqttAndroidClient;

	public static native void onConnected(String guid);
	public static native void onDisconnected(String guid);
	public static native void onSubscribed(int messageId, int[] qos, String guid);
	public static native void onUnsubscribed(int messageId, String guid);
	public static native void onPublished(int messageId, String guid);
	public static native void onMessageArrived(String topic, MqttMessage message, String guid);
	public static native void onError(int errCode, String errMessage, String guid);

	private String m_Guid;

	public MqttHelper(Activity activity, String serverUri, String clientId, String guid) {
		mqttAndroidClient = new MqttAndroidClient(activity, serverUri, clientId);
		m_Guid = guid;
	}

	public void connect(MqttConnectOptions options) {
		try {
			mqttAndroidClient.connect(options, null, new IMqttActionListener() {
				@Override
				public void onSuccess(IMqttToken asyncActionToken) {
					onConnected(m_Guid);
				}

				@Override
				public void onFailure(IMqttToken asyncActionToken, Throwable exception) {
					MqttException e = asyncActionToken.getException();
					onError(e.getReasonCode(), e.getMessage(), m_Guid);
				}
			});
		} catch (MqttException e) {
			onError(e.getReasonCode(), e.getMessage(), m_Guid);
		}
	}

	public void disconnect(int quiesceTimeout) {
		try {
			if (!mqttAndroidClient.isConnected()) {
				Log.d(TAG, "MQTT => There is no active connection");
				return;
			}

			mqttAndroidClient.disconnect(quiesceTimeout, null, new IMqttActionListener() {
				@Override
				public void onSuccess(IMqttToken asyncActionToken) {
					onDisconnected(m_Guid);
				}

				@Override
				public void onFailure(IMqttToken asyncActionToken, Throwable exception) {
					MqttException e = asyncActionToken.getException();
					onError(e.getReasonCode(), e.getMessage(), m_Guid);
				}
			});
		} catch (MqttException e) {
			onError(e.getReasonCode(), e.getMessage(), m_Guid);
		}
	}

	public void setDisconnectedBufferOptions(DisconnectedBufferOptions disconnectedBufferOptions) {
		mqttAndroidClient.setBufferOpts(disconnectedBufferOptions);
	}

	public void subscribeToTopic(final String topic, final int qos) {
		try {
			if (!mqttAndroidClient.isConnected()) {
				Log.d(TAG, "MQTT => There is no active connection");
				return;
			}

			mqttAndroidClient.subscribe(topic, qos, this, new IMqttActionListener() {
				@Override
				public void onSuccess(IMqttToken asyncActionToken) {
					onSubscribed(asyncActionToken.getMessageId(), new int[] {qos}, m_Guid);
				}

				@Override
				public void onFailure(IMqttToken asyncActionToken, Throwable exception) {
					MqttException e = asyncActionToken.getException();
					onError(e.getReasonCode(), e.getMessage(), m_Guid);
				}
			});

			mqttAndroidClient.subscribe(topic, qos, new IMqttMessageListener() {
				@Override
				public void messageArrived(String topic, MqttMessage message) {
					onMessageArrived(topic, message, m_Guid);
				}
			});
		} catch (MqttException e) {
			onError(e.getReasonCode(), e.getMessage(), m_Guid);
		}
	}

	public void unsubscribeFromTopic(final String topic) {
		try {
			if (!mqttAndroidClient.isConnected()) {
				Log.d(TAG, "MQTT => There is no active connection");
				return;
			}

			mqttAndroidClient.unsubscribe(topic, null, new IMqttActionListener() {
				@Override
				public void onSuccess(IMqttToken asyncActionToken) {
					onUnsubscribed(asyncActionToken.getMessageId(), m_Guid);
				}

				@Override
				public void onFailure(IMqttToken asyncActionToken, Throwable exception) {
					MqttException e = asyncActionToken.getException();
					onError(e.getReasonCode(), e.getMessage(), m_Guid);
				}
			});
		} catch (MqttException e) {
			onError(e.getReasonCode(), e.getMessage(), m_Guid);
		}
	}

	public void publishMessage(MqttMessage message, String topic) {
		try {
			if (!mqttAndroidClient.isConnected()) {
				Log.d(TAG, "MQTT => There is no active connection");
				return;
			}

			mqttAndroidClient.publish(topic, message, null, new IMqttActionListener() {
				@Override
				public void onSuccess(IMqttToken asyncActionToken) {
					onPublished(asyncActionToken.getMessageId(), m_Guid);
				}

				@Override
				public void onFailure(IMqttToken asyncActionToken, Throwable exception) {
					MqttException e = asyncActionToken.getException();
					onError(e.getReasonCode(), e.getMessage(), m_Guid);
				}
			});
		} catch (MqttException e) {
			onError(e.getReasonCode(), e.getMessage(), m_Guid);
		}
	}

	public static String stringFromByteArray(byte[] data) {
		return new String(data);
	}
}
