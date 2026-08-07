<script lang="ts">
	import { page } from '$app/stores';

	import Chat from '$features/chat/Chat.svelte';
	import Help from '$shared/layout/Help.svelte';
</script>

<Help />
<Chat chatIdProp={$page.params.id} />
